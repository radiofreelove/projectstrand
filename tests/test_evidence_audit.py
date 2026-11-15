#!/usr/bin/env python3
"""
Tests for tests/evidence_audit.py, against fixtures on this computer.

    python3 tests/test_evidence_audit.py

No request leaves the machine. The fixtures are in tests/fixtures/evidence/.
The first tests feed the tool small pieces of HTML and made-up baselines.
The last ones run the whole tool against a small server on 127.0.0.1 that
copies the ways a source can answer:

  - a web page that keeps its words while its markup and scripts change
  - a web page whose fee changes after the baseline
  - a PDF, compared by its bytes
  - a server that answers 403 to this tool
  - an address that robots.txt keeps out
  - a page that is gone (404)
  - a source added after the baseline was written

Fails (exit 1) if any test fails. Needs PyYAML, like the tool.
"""
from __future__ import annotations

import contextlib
import http.server
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evidence_audit as audit  # noqa: E402

FIXTURES = HERE / "fixtures" / "evidence"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class Normalization(unittest.TestCase):
    def test_html_becomes_the_words_a_reader_sees(self):
        text = audit.html_text(fixture("page-before.html").decode())
        self.assertEqual(text, "Change a birth record\nHome\nForms\nChange a birth record\n"
                               "The amendment fee is $35. The form is OHA 2673.\n"
                               "Notarized application\nNo court order")

    def test_markup_scripts_and_styles_do_not_change_the_hash(self):
        # Same words; different tags, attributes, scripts, styles, entities, and line breaks.
        first = audit.normalize(fixture("page-before.html"), "text/html; charset=utf-8")
        second = audit.normalize(fixture("page-markup-only.html"), "text/html")
        self.assertEqual(first[0], "text")
        self.assertEqual(first, second)
        self.assertNotEqual(first[2], audit.normalize(fixture("page-after.html"), "text/html")[2])

    def test_same_words_same_hash(self):
        a = audit.normalize(b"<p>One   two</p>\n<p>three</p>", "text/html")
        b = audit.normalize(b"<html><body><p>One two</p><script>x()</script><p>three</p></body></html>",
                            "text/html")
        self.assertEqual(a[1], "One two\nthree")
        self.assertEqual(a[2], b[2])
        self.assertEqual(a[3], len("One two\nthree"))

    def test_changed_words_change_the_hash(self):
        a = audit.normalize(b"<p>The fee is $35.</p>", "text/html")
        b = audit.normalize(b"<p>The fee is $40.</p>", "text/html")
        self.assertNotEqual(a[2], b[2])

    def test_pdf_is_compared_by_its_bytes(self):
        body = fixture("form.pdf")
        mode, text, digest, length = audit.normalize(body, "application/octet-stream")
        self.assertEqual((mode, text, length), ("bytes", None, len(body)))
        import hashlib
        self.assertEqual(digest, hashlib.sha256(body).hexdigest())
        # A PDF is a PDF whatever the server calls it.
        self.assertEqual(audit.normalize(body, "")[0], "bytes")
        self.assertEqual(audit.normalize(b"not really", "application/pdf")[0], "bytes")

    def test_html_without_a_content_type_is_still_html(self):
        mode, text, _, _ = audit.normalize(b"<!doctype html><title>T</title><p>Words</p>", "")
        self.assertEqual((mode, text), ("text", "T\nWords"))

    def test_plain_text_is_collapsed(self):
        mode, text, _, _ = audit.normalize(b"a   b\n\n\n  c  ", "text/plain")
        self.assertEqual((mode, text), ("text", "a b\nc"))

    def test_other_files_are_bytes(self):
        self.assertEqual(audit.normalize(b"\x89PNG....", "image/png")[0], "bytes")

    def test_charset_is_respected(self):
        _, text, _, _ = audit.normalize("<p>Fé</p>".encode("latin-1"), "text/html; charset=ISO-8859-1")
        self.assertEqual(text, "Fé")


class Classification(unittest.TestCase):
    URL = "https://example.test/a"

    def entry(self, digest="abc", url=URL):
        return {"id": "s", "url": url, "sha256": digest, "mode": "text", "fetched": "2026-11-15"}

    def test_every_state(self):
        fetched = {"state": audit.FETCHED, "sha256": "abc", "mode": "text"}
        self.assertEqual(audit.classify(fetched, self.entry(), self.URL), audit.UNCHANGED)
        self.assertEqual(audit.classify(fetched, self.entry("xyz"), self.URL), audit.CHANGED)
        self.assertEqual(audit.classify({"state": audit.BLOCKED}, self.entry(), self.URL), audit.BLOCKED)
        self.assertEqual(audit.classify({"state": audit.UNREACHABLE}, self.entry(), self.URL), audit.UNREACHABLE)

    def test_no_hash_is_never_a_change(self):
        fetched = {"state": audit.FETCHED, "sha256": "abc", "mode": "text"}
        self.assertEqual(audit.classify(fetched, None, self.URL), audit.NOT_BASELINED)
        self.assertEqual(audit.classify(fetched, self.entry(None), self.URL), audit.NOT_BASELINED)
        # A new address is a new source as far as the baseline knows.
        self.assertEqual(audit.classify(fetched, self.entry(url="https://example.test/b"), self.URL),
                         audit.NOT_BASELINED)

    def fake_opener(self, error):
        def opener(request):
            raise error
        return opener

    def test_401_and_403_are_checker_blocked_not_dead(self):
        for code in (401, 403):
            err = urllib.error.HTTPError(self.URL, code, "no", {}, None)
            result = audit.fetch(self.URL, opener=self.fake_opener(err))
            self.assertEqual(result["state"], audit.BLOCKED)
            self.assertIn(str(code), result["note"])

    def test_other_errors_are_unreachable(self):
        err = urllib.error.HTTPError(self.URL, 404, "gone", {}, None)
        self.assertEqual(audit.fetch(self.URL, opener=self.fake_opener(err))["state"], audit.UNREACHABLE)
        err = urllib.error.URLError(ConnectionRefusedError("refused"))
        self.assertEqual(audit.fetch(self.URL, opener=self.fake_opener(err))["state"], audit.UNREACHABLE)
        self.assertEqual(audit.fetch(self.URL, opener=self.fake_opener(TimeoutError()))["note"], "timed out")

    def test_a_reply_cut_short_is_asked_for_again_once(self):
        import http.client
        calls = []

        def opener(request):
            calls.append(1)
            raise http.client.IncompleteRead(b"part")

        original, audit.PAUSE = audit.PAUSE, 0
        try:
            result = audit.fetch(self.URL, opener=opener)
        finally:
            audit.PAUSE = original
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["state"], audit.UNREACHABLE)
        self.assertIn("asked twice", result["note"])

    def test_robots_refusal_is_checker_blocked(self):
        class Rules:
            def check(self, url):
                return False, "robots.txt asks automated visitors not to load this address"

        rows = list(audit.fetch_all([{"id": "s", "url": self.URL}], fetcher=lambda url: self.fail("fetched"),
                                    robots=Rules(), sleep=lambda s: None))
        self.assertEqual(rows[0][1]["state"], audit.BLOCKED)

    def test_robots_txt_answering_403_means_stay_out(self):
        err = urllib.error.HTTPError(self.URL, 403, "no", {}, None)
        allowed, note = audit.Robots(opener=self.fake_opener(err)).check(self.URL)
        self.assertFalse(allowed)
        self.assertIn("robots.txt", note)

    def test_missing_robots_txt_allows(self):
        err = urllib.error.HTTPError(self.URL, 404, "none", {}, None)
        self.assertEqual(audit.Robots(opener=self.fake_opener(err)).check(self.URL), (True, None))

    def test_requests_are_one_at_a_time_with_a_pause(self):
        slept = []

        class Allow:
            def check(self, url):
                return True, None

        entries = [{"id": str(i), "url": f"https://example.test/{i}"} for i in range(3)]
        list(audit.fetch_all(entries, fetcher=lambda url: {"state": audit.UNREACHABLE, "note": "x"},
                             robots=Allow(), pause=1.0, host_pause=2.0, sleep=slept.append))
        self.assertEqual(len(slept), 2)  # none before the first request
        self.assertTrue(all(s > 1.5 for s in slept))

    def test_bounded_diff_is_bounded(self):
        old = "\n".join(f"line {i}" for i in range(200))
        new = "\n".join(f"line {i} changed" for i in range(200))
        diff = audit.bounded_diff(old, new, limit=10)
        self.assertEqual(len(diff.splitlines()), 11)
        self.assertIn("more diff lines not shown", diff)
        self.assertNotIn("```", audit.bounded_diff("a", "```b"))


class Baseline(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_missing_file_is_an_empty_baseline(self):
        self.assertEqual(audit.load_baseline(self.tmp / "none.yml"), {})

    def test_round_trip_keeps_every_field(self):
        src = {"id": "s1", "url": "https://example.test/", "checked": __import__("datetime").date(2026, 11, 3)}
        entry = audit.baseline_entry(src, {"state": "fetched", "mode": "text", "sha256": "ab" * 32,
                                           "length": 12}, "2026-11-15")
        blocked = audit.baseline_entry({"id": "s2", "url": "https://example.test/b", "checked": "2026-11-03"},
                                       {"state": audit.BLOCKED, "note": "the site answered 403 to this tool"},
                                       "2026-11-15")
        path = self.tmp / "b.yml"
        audit.save_baseline(path, [entry, blocked])
        text = path.read_text()
        self.assertTrue(text.startswith("# What each source"))
        self.assertIn("November 2026 verified source", text)
        loaded = audit.load_baseline(path)
        self.assertEqual(loaded["s1"], entry)
        self.assertEqual(loaded["s1"]["registry_checked"], "2026-11-03")
        self.assertEqual(loaded["s2"]["state"], audit.BLOCKED)
        self.assertNotIn("sha256", loaded["s2"])
        for key in ("url", "fetched", "state", "mode", "sha256", "length"):
            self.assertIn(key, loaded["s1"])

    def test_refresh_never_throws_away_a_hash_it_cannot_replace(self):
        old = {"a": {"id": "a", "url": "u", "sha256": "1"}, "b": {"id": "b", "url": "v", "sha256": "2"},
               "gone": {"id": "gone", "url": "w", "sha256": "3"}}
        fresh = {"a": {"id": "a", "url": "u", "sha256": None, "state": audit.BLOCKED},
                 "b": {"id": "b", "url": "v", "sha256": "9", "state": "fetched"}}
        entries, kept = audit.merge_baseline(old, fresh, ["a", "b", "c"])
        self.assertEqual([e["sha256"] for e in entries], ["1", "9"])
        self.assertEqual(kept, ["a"])

    def test_a_moved_address_is_not_kept(self):
        old = {"a": {"id": "a", "url": "old", "sha256": "1"}}
        fresh = {"a": {"id": "a", "url": "new", "sha256": None, "state": audit.UNREACHABLE}}
        entries, kept = audit.merge_baseline(old, fresh, ["a"])
        self.assertEqual((entries[0]["url"], kept), ("new", []))

    def test_snapshot_only_counts_when_it_matches_the_hash(self):
        audit.save_snapshot(self.tmp, "s/1", "words")
        good = audit.normalize(b"words", "text/plain")[2]
        self.assertEqual(audit.load_snapshot(self.tmp, "s/1", good), "words")
        self.assertIsNone(audit.load_snapshot(self.tmp, "s/1", "0" * 64))


class Exposure(unittest.TestCase):
    def setUp(self):
        import yaml
        self.facts = yaml.safe_load(fixture("facts.yml"))
        self.report = json.loads(fixture("build-report.json"))

    def test_facts_that_cite_a_source_and_the_pages_that_show_them(self):
        usage = audit.fact_pages(self.report)
        self.assertEqual(audit.exposure("fx-changes", self.facts, usage),
                         [("fx_amend_fee", ["oregon", "path"]), ("fx_form_name", ["oregon"]),
                          ("fx_unrendered", [])])
        self.assertEqual(audit.exposure("fx-pdf", self.facts, usage), [("fx_form_name", ["oregon"])])
        self.assertEqual(audit.exposure("fx-blocked", self.facts, usage), [])

    def test_without_a_build_report_pages_are_unknown_not_empty(self):
        self.assertEqual(audit.exposure("fx-pdf", self.facts, None), [("fx_form_name", None)])

    def test_an_old_build_report_without_facts_is_not_used(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "r.json").write_text(json.dumps({"pages": [{"slug": "a", "sources": []}]}))
            self.assertIsNone(audit.load_build_report(tmp / "r.json"))
            self.assertIsNone(audit.load_build_report(tmp / "missing.json"))
        finally:
            shutil.rmtree(tmp)

    def test_the_real_build_records_facts_per_page(self):
        """build.py's fact() records what each page rendered, so the map comes from the build."""
        report = audit.load_build_report()
        if report is None:
            self.skipTest("run python3 build.py first")
        usage = audit.fact_pages(report)
        self.assertIn("utah", usage.get("ut_fee_petition", []))
        self.assertIn("index", usage.get("ut_fee_petition", []))


# ---------------------------------------------------------------------------
# The whole tool, against a server on this computer

class Handler(http.server.BaseHTTPRequestHandler):
    phase = "before"
    requests: list = []

    def log_message(self, *args):
        pass

    def send(self, code, body=b"", ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Handler.requests.append((self.path, self.headers.get("User-Agent")))
        if self.path == "/robots.txt":
            return self.send(200, fixture("robots.txt"), "text/plain")
        if self.path == "/page":
            name = "page-before.html" if Handler.phase == "before" else "page-markup-only.html"
            return self.send(200, fixture(name))
        if self.path == "/changes":
            return self.send(200, fixture("page-before.html" if Handler.phase == "before" else "page-after.html"))
        if self.path == "/form.pdf":
            return self.send(200, fixture("form.pdf"), "application/pdf")
        if self.path == "/new":
            return self.send(200, b"<p>New source</p>")
        if self.path == "/forbidden":
            return self.send(403, b"no robots")
        return self.send(404, b"not found")


class WholeRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.pauses = (audit.PAUSE, audit.HOST_PAUSE)
        audit.PAUSE = audit.HOST_PAUSE = 0.0
        fetch_all = audit.fetch_all
        cls.fetch_all = fetch_all
        audit.fetch_all = lambda entries, **kw: fetch_all(entries, pause=0, host_pause=0, **kw)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        audit.PAUSE, audit.HOST_PAUSE = cls.pauses
        audit.fetch_all = cls.fetch_all

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        text = (FIXTURES / "sources.yml").read_text().replace("{base}", self.base)
        (self.tmp / "sources.yml").write_text(text)
        Handler.phase, Handler.requests = "before", []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_tool(self, *extra):
        args = ["--registry", str(self.tmp / "sources.yml"), "--baseline", str(self.tmp / "baseline.yml"),
                "--facts", str(FIXTURES / "facts.yml"), "--build-report", str(FIXTURES / "build-report.json"),
                "--snapshots", str(self.tmp / "snap"), "--today", "2026-11-16", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = audit.main(args)
        return code, out.getvalue()

    def write_baseline_without_new(self):
        text = (self.tmp / "sources.yml").read_text()
        (self.tmp / "sources.yml").write_text(text.split("- id: fx-new")[0])
        code, _ = self.run_tool("--write-baseline")
        (self.tmp / "sources.yml").write_text(text)
        return code

    def test_write_baseline_then_compare(self):
        self.assertEqual(self.write_baseline_without_new(), 0)
        base = audit.load_baseline(self.tmp / "baseline.yml")
        self.assertEqual(base["fx-page"]["mode"], "text")
        self.assertEqual(base["fx-pdf"]["mode"], "bytes")
        self.assertEqual(base["fx-blocked"]["state"], audit.BLOCKED)
        self.assertEqual(base["fx-robots"]["state"], audit.BLOCKED)
        self.assertEqual(base["fx-gone"]["state"], audit.UNREACHABLE)
        self.assertNotIn("sha256", base["fx-gone"])
        # robots.txt was respected: the kept-out address was never asked for.
        self.assertNotIn("/private/page", [path for path, _ in Handler.requests])
        self.assertTrue(all(agent == audit.USER_AGENT for _, agent in Handler.requests))

        # Unchanged words compare equal; a fee change is a change.
        Handler.phase = "after"
        report_path = self.tmp / "report.md"
        results_path = self.tmp / "results.json"
        code, _ = self.run_tool("--report", str(report_path), "--results", str(results_path))
        self.assertEqual(code, 1)
        states = {r["id"]: r["state"] for r in json.loads(results_path.read_text())["results"]}
        self.assertEqual(states, {"fx-page": audit.UNCHANGED, "fx-changes": audit.CHANGED,
                                  "fx-pdf": audit.UNCHANGED, "fx-blocked": audit.BLOCKED,
                                  "fx-robots": audit.BLOCKED, "fx-gone": audit.UNREACHABLE,
                                  "fx-new": audit.NOT_BASELINED})
        report = report_path.read_text()
        self.assertIn("### fx-changes", report)
        self.assertIn("-The amendment fee is $35. The form is OHA 2673.", report)
        self.assertIn("+The amendment fee is $40. The form is OHA 2673.", report)
        self.assertIn("  - fx_amend_fee: oregon, path", report)
        self.assertIn("  - fx_unrendered: no page", report)
        self.assertIn("Pages that cite it directly, not through a fact: sources", report)
        self.assertIn("not a dead link", report)
        self.assertIn("- fx-new:", report.split("## Not yet baselined")[1])
        # The baseline itself is never rewritten by a comparison.
        self.assertEqual(audit.load_baseline(self.tmp / "baseline.yml"), base)

    def test_no_change_exits_0_even_with_blocked_and_unreachable(self):
        self.write_baseline_without_new()
        code, out = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("| Checker-blocked | 2 |", out)
        self.assertIn("| Unreachable | 1 |", out)

    def test_a_changed_pdf_is_lower_confidence(self):
        self.write_baseline_without_new()
        entries = audit.load_baseline(self.tmp / "baseline.yml")
        entries["fx-pdf"]["sha256"] = "0" * 64
        audit.save_baseline(self.tmp / "baseline.yml", list(entries.values()))
        code, out = self.run_tool("--only", "fx-pdf")
        self.assertEqual(code, 1)
        self.assertIn("Lower confidence", out)
        self.assertIn("  - fx_form_name: oregon", out)

    def test_no_baseline_at_all_is_not_a_change(self):
        code, out = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("| Changed | 0 |", out)
        self.assertIn("## Not yet baselined (7)", out)

    def test_unknown_only_id_is_a_usage_error(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.run_tool("--only", "nope")[0], 2)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
