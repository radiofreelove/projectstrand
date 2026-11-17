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
import hashlib
import http.server
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import evidence_audit as audit  # noqa: E402

# The hash of the comparison-rules block, the same in both projects (see OneSetOfRules).
RULES_BLOCK_SHA256 = "1e34858acd2a520b6c39ba569c912a4a17d5e465b2deb1f63ae765933b6dea1f"

FIXTURES = HERE / "fixtures" / "evidence"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


# Every real source has well over audit.MIN_WORDS words; a reply with fewer is
# not taken as the source. Pages these tests have the tool fetch or carry
# forward get this paragraph, so they are the size of a real page.
ENOUGH = ("To change the sex on a birth record, send the signed application, a copy of your photo ID, and the "
          "fee to the state vital records office. You do not need a court order or a letter from a doctor. A "
          "parent or guardian signs for a minor. The office mails the new certificate, and the old one is "
          "sealed. Ask the office if you need help with the fee.")


def served(body: bytes) -> bytes:
    """A fixture page as a real site would serve it: long enough to be a source."""
    paragraph = f"<p>{ENOUGH}</p>".encode()
    return body.replace(b"</body>", paragraph + b"</body>") if b"</body>" in body else body + paragraph


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

    def test_volatile_lines_are_dropped_only_for_their_source(self):
        text = "Find legal help\nN2\nExternal Link Warning"
        self.assertEqual(audit.drop_volatile(text, "wa-courts-forms"), "Find legal help\nExternal Link Warning")
        self.assertEqual(audit.drop_volatile(text, "or-ojd-forms"), text)
        form = "CAPTCHA\nComments\nThis field is for validation purposes and should be left unchanged.\nSend"
        self.assertEqual(audit.drop_volatile(form, "us-lambda-helpdesk"),
                         "CAPTCHA\nThis field is for validation purposes and should be left unchanged.\nSend")
        one = audit.apply_volatile({"state": audit.FETCHED, "mode": "text", "text": text,
                                    "sha256": "x", "length": 0}, "wa-courts-forms")
        two = audit.apply_volatile({"state": audit.FETCHED, "mode": "text", "text": text.replace("N2", "N1"),
                                    "sha256": "y", "length": 0}, "wa-courts-forms")
        self.assertEqual(one["sha256"], two["sha256"])
        self.assertIn("change on every load", one["note"])

    def test_charset_is_respected(self):
        _, text, _, _ = audit.normalize("<p>Fé</p>".encode("latin-1"), "text/html; charset=ISO-8859-1")
        self.assertEqual(text, "Fé")


class Classification(unittest.TestCase):
    URL = "https://example.test/a"

    def entry(self, digest="abc", url=URL):
        return {"id": "s", "url": url, "sha256": digest, "mode": "text", "fetched": "2026-11-15", "rules": audit.RULES}

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
        old = {"a": {"id": "a", "url": "u", "sha256": "1", "rules": audit.RULES},
               "b": {"id": "b", "url": "v", "sha256": "2", "rules": audit.RULES},
               "gone": {"id": "gone", "url": "w", "sha256": "3", "rules": audit.RULES}}
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
# The comparison rules. Each class below copies one way an unchanged source
# looked changed in November 2026, and fails under the rules before RULES 2.

class LineBreaksAndSpaces(unittest.TestCase):
    """The same words, with the lines broken in other places, are the same text."""

    # The header of an Oregon.gov page, as two computers turned it into text.
    SPLIT = ("Skip to main content\nAn official website of the State of Oregon\nLearn\nHow you know »\n"
             "Please call 800-699-9075, go to\nBenefits.Oregon.gov, or\nvisit your local office.\nContact Us\n\u200b\nMedia")
    JOINED = ("Skip to main content\nAn official website of the State of Oregon Learn How you know »\n"
              "Please call 800-699-9075, go to Benefits.Oregon.gov, or visit your local office.\nContact Us\n\u200b Media")

    def test_where_lines_break_does_not_change_the_hash(self):
        self.assertEqual(audit.text_digest(self.SPLIT), audit.text_digest(self.JOINED))

    def test_the_hash_is_the_canonical_words(self):
        self.assertEqual(audit.canonical("A\n  b\tc\u00a0d \u200b\ne\u00ad"), "A b c d e")

    def test_a_changed_word_still_changes_the_hash(self):
        self.assertNotEqual(audit.text_digest(self.JOINED), audit.text_digest(self.JOINED.replace("800-699", "800-698")))

    def test_html_with_other_line_breaks_hashes_the_same(self):
        one = b"<html><body><p>Please call 800-699-9075, go to\n<a href=x>Benefits.Oregon.gov</a>, or visit.</p></body></html>"
        two = b"<html><body><p>Please call 800-699-9075, go to <a href=x>Benefits.Oregon.gov</a>,\n  or visit.</p></body></html>"
        self.assertEqual(audit.normalize(one, "text/html")[2], audit.normalize(two, "text/html")[2])

    def test_a_line_join_is_not_shown_as_a_change(self):
        self.assertEqual(audit.bounded_diff(self.SPLIT, self.JOINED), "")

    def test_a_changed_word_is_shown_with_its_line(self):
        diff = audit.bounded_diff(self.SPLIT, self.JOINED.replace("local office", "nearest office"))
        self.assertIn("-visit your local office.", diff)
        self.assertIn("+Please call 800-699-9075, go to Benefits.Oregon.gov, or visit your nearest office.", diff)
        self.assertNotIn("Learn", diff)

    def test_words_added_at_the_end_are_shown(self):
        diff = audit.bounded_diff("One\nTwo", "One Two\nThree\nFour")
        self.assertEqual(diff, "@@ after: One Two @@\n+Three\n+Four")


class WholeReplies(unittest.TestCase):
    """A reply that is not all there is never hashed."""

    def test_a_reply_shorter_than_its_content_length_is_cut_short(self):
        with self.assertRaises(audit.CutShort):
            audit.check_whole(b"<html><p>Where to send", "text/html", "118961")
        audit.check_whole(b"<html><p>All</p></html>", "text/html", "23")

    def test_a_pdf_without_a_length_must_end_with_its_marker(self):
        with self.assertRaises(audit.CutShort):
            audit.check_whole(b"%PDF-1.7\n1 0 obj", "application/pdf", None)
        audit.check_whole(b"%PDF-1.7\n1 0 obj\n%%EOF\n", "application/pdf", None)

    def test_the_same_cut_twice_is_cut_short_both_times(self):
        # U08 (The Stasis Project), Nov. 2026: three of six fetches stopped at the same 81,642 of
        # 209,710 bytes. Under rules 1 two such fetches hashed the same, and the
        # PDF would have been called unchanged on a tenth of its bytes.
        part = b"%PDF-1.7\n" + b"x" * 81_633
        for _ in range(2):
            with self.assertRaises(audit.CutShort):
                audit.check_whole(part, "application/pdf", "209710")

    def test_a_whole_pdf_with_a_length_needs_no_marker(self):
        audit.check_whole(b"%PDF-1.7 x", "application/pdf", "10")

    def test_a_page_without_closing_tags_is_whole(self):
        # Some real pages end without </body> or </html>, and are whole.
        audit.check_whole(b"<!doctype html><html><body><p>News</p><style>.x{}</style>", "text/html", None)


class NotTheSource(unittest.TestCase):
    """A page that checks for automated visitors, or has no words, is never hashed."""

    def test_a_check_for_automated_visitors_is_checker_blocked(self):
        body = b"<html><body><h1>One moment, please...</h1><p>Please wait while your request is being verified...</p></body></html>"
        result = audit.examine(body, "text/html", str(len(body)))
        self.assertEqual(result["state"], audit.BLOCKED)
        self.assertNotIn("sha256", result)
        self.assertIn("check for automated visitors", result["note"])

    def test_a_captcha_page_is_checker_blocked(self):
        body = (b"<html><body><p>Your request has been flagged as potentially automated. If you are human user "
                b"receiving this message, please complete the CAPTCHA</p></body></html>")
        self.assertEqual(audit.examine(body, "text/html", None)["state"], audit.BLOCKED)

    def test_a_page_with_no_words_is_checker_blocked(self):
        body = (b'<html><head><meta http-equiv="refresh" content="0;/.well-known/sgcaptcha/?r=%2F"></meta>'
                b"</head></html>")
        result = audit.examine(body, "text/html", None)
        self.assertEqual(result["state"], audit.BLOCKED)
        self.assertIn("no readable words", result["note"])

    def test_a_page_too_short_to_be_the_source_is_checker_blocked(self):
        # A check page in words no list has yet. Hashed, it would match itself
        # on the next fetch, and the source would be called unchanged unread.
        body = b"<html><body><noscript></noscript><div id=root>You need to enable JavaScript to run this app.</div></body></html>"
        result = audit.examine(body, "text/html", str(len(body)))
        self.assertEqual(result["state"], audit.BLOCKED)
        self.assertNotIn("sha256", result)
        self.assertIn("only 9 words", result["note"])

    def test_the_same_check_page_twice_is_never_unchanged(self):
        # S27 (The Stasis Project), Nov. 2026: the baseline and the next fetch were the same CAPTCHA
        # page, with lines broken differently. Under rules 1 only the line breaks
        # made it "changed"; with them ignored it would have been "unchanged".
        page = ("<html><body><h1>Request Access</h1><p>Due to aggressive automated scraping of FederalRegister.gov "
                "and eCFR.gov, programmatic access to these sites is limited to access to our extensive developer "
                "APIs.</p><p>Your request has been flagged as potentially automated. If you are human user receiving "
                "this message, please complete the CAPTCHA (bot test) below and click \"Request Access\". You may "
                "occassionally be asked to complete the CAPTCHA again, this is normal and part of our security "
                "measures.</p></body></html>")
        for body in (page, page.replace(" ", "\n", 9)):
            self.assertEqual(audit.examine(body.encode(), "text/html", None)["state"], audit.BLOCKED)

    def test_other_common_checks_are_checker_blocked(self):
        for words in ("Just a moment... Verifying you are human. This may take a few seconds. example.gov needs to "
                      "review the security of your connection before proceeding.",
                      "Request unsuccessful. Incapsula incident ID: 1234-5678",
                      "Pardon Our Interruption. As you were browsing something about your browser made us think "
                      "you were a bot."):
            body = f"<html><body><p>{words}</p></body></html>".encode()
            self.assertEqual(audit.examine(body, "text/html", None)["state"], audit.BLOCKED, words)

    def test_the_shortest_real_source_is_read(self):
        # The shortest source text in November 2026 (U22, The Stasis Project) had 165 words.
        body = ("<html><body><p>" + " ".join([ENOUGH] * 3) + "</p></body></html>").encode()
        self.assertGreaterEqual(len(audit.canonical(audit.html_text(body.decode())).split()), 165)
        self.assertEqual(audit.examine(body, "text/html", None)["state"], audit.FETCHED)

    def test_a_long_page_that_quotes_a_phrase_is_read(self):
        body = ("<html><body><p>" + "Words. " * 600 + "verify you are human</p></body></html>").encode()
        self.assertEqual(audit.examine(body, "text/html", None)["state"], audit.FETCHED)

    def test_a_pdf_is_never_called_a_check_page(self):
        body = b"%PDF-1.7\n%%EOF"
        self.assertEqual(audit.examine(body, "application/pdf", None)["mode"], "bytes")


class RulesVersions(unittest.TestCase):
    """A hash written under other rules is never compared, and can be carried forward."""
    URL = "https://example.test/a"
    TEXT = "Work rules\nThe rules start\nJan. 1, 2027.\n" + ENOUGH

    def old(self, text=TEXT, **extra):
        """An entry as the tool wrote it before RULES: no "rules", the saved text hashed as it was."""
        return dict({"id": "T1", "url": self.URL, "fetched": "2026-11-15", "state": audit.FETCHED, "mode": "text",
                     "sha256": hashlib.sha256(text.encode()).hexdigest(), "length": len(text)}, **extra)

    def test_an_old_rules_entry_is_not_yet_baselined_never_changed(self):
        now = {"state": audit.FETCHED, "mode": "text", "text": self.TEXT, "sha256": audit.text_digest(self.TEXT)}
        self.assertEqual(audit.classify(now, self.old(), self.URL), audit.NOT_BASELINED)
        self.assertTrue(audit.older_rules(self.old(), self.URL))

    def test_a_refresh_keeps_an_old_rules_hash_it_cannot_replace(self):
        # Nov. 16, 2026: a refresh of The Stasis Project's baseline that could not
        # read ten sources wrote "unreachable" over their only hashes. Kept, a
        # hash can still be carried forward or checked against the next whole fetch.
        blocked = {"id": "T1", "url": self.URL, "state": audit.UNREACHABLE, "sha256": None}
        merged, kept = audit.merge_baseline({"T1": self.old()}, {"T1": blocked}, ["T1"])
        self.assertEqual(merged[0], self.old())
        self.assertEqual(kept, ["T1"])
        # Kept, but still never compared.
        now = {"state": audit.FETCHED, "mode": "text", "sha256": audit.text_digest(self.TEXT)}
        self.assertEqual(audit.classify(now, merged[0], self.URL), audit.NOT_BASELINED)

    def test_a_refresh_still_drops_an_old_rules_hash_for_another_address(self):
        moved = {"id": "T1", "url": "https://example.test/new", "state": audit.UNREACHABLE, "sha256": None}
        merged, kept = audit.merge_baseline({"T1": self.old()}, {"T1": moved}, ["T1"])
        self.assertIsNone(merged[0]["sha256"])
        self.assertEqual(kept, [])

    def test_carrying_forward_rehashes_the_saved_text(self):
        carried, why = audit.carry_forward(self.old(), self.TEXT)
        self.assertIsNone(why)
        self.assertEqual((carried["rules"], carried["sha256"]), (audit.RULES, audit.text_digest(self.TEXT)))
        joined = {"state": audit.FETCHED, "mode": "text", "sha256": audit.text_digest(self.TEXT.replace("\n", " "))}
        self.assertEqual(audit.classify(joined, carried, self.URL), audit.UNCHANGED)

    def test_carrying_forward_needs_the_text_the_baseline_hashed(self):
        self.assertIsNone(audit.carry_forward(self.old(), "other words")[0])
        self.assertIsNone(audit.carry_forward(self.old(), None)[0])

    def test_a_check_page_is_never_carried_forward(self):
        page = "One moment, please...\nPlease wait while your request is being verified..."
        carried, why = audit.carry_forward(self.old(page), page)
        self.assertIsNone(carried)
        self.assertIn("not the source", why)

    def test_a_bytes_entry_is_never_carried_forward(self):
        # Under rules 1, 9 of The Stasis Project's 37 PDF hashes were of replies
        # cut short. There is no saved copy to re-take a bytes hash from, so it is
        # written again from a whole fetch instead.
        carried, why = audit.carry_forward(self.old(mode="bytes"), None)
        self.assertIsNone(carried)
        self.assertIn("not known", why)

    def test_a_stub_is_never_carried_forward(self):
        stub = "Loading\nPlease enable JavaScript to view this page."
        carried, why = audit.carry_forward(self.old(stub), stub)
        self.assertIsNone(carried)
        self.assertIn("too few to be the source", why)


class EarlierHash(unittest.TestCase):
    """A fresh fetch that replaces a hash says whether it says what that hash said."""
    URL = "https://example.test/a"

    def old(self, digest, mode="text", rules=None):
        made = {"id": "T1", "url": self.URL, "fetched": "2026-11-15", "state": audit.FETCHED, "mode": mode,
                "sha256": digest}
        if rules:
            made["rules"] = rules
        return made

    def now(self, mode, digest):
        return {"state": audit.FETCHED, "mode": mode, "sha256": digest}

    def test_the_same_bytes_carry_the_check_forward(self):
        said = audit.compared_with_earlier(self.old("abc", "bytes"), self.now("bytes", "abc"), self.URL, None)
        self.assertEqual(said, "the same as the entry of 2026-11-15 (rules 1)")

    def test_a_cut_short_old_hash_is_reported_different(self):
        whole, part = b"%PDF-1.7 whole file %%EOF", b"%PDF-1.7 whole"
        said = audit.compared_with_earlier(self.old(hashlib.sha256(part).hexdigest(), "bytes"),
                                           self.now("bytes", hashlib.sha256(whole).hexdigest()), self.URL, None)
        self.assertTrue(said.startswith("different from the entry of 2026-11-15"))

    def test_old_text_is_compared_under_the_new_rules(self):
        split, joined = "Please call 800-699-9075, go to\nBenefits.Oregon.gov", "Please call 800-699-9075, go to Benefits.Oregon.gov"
        old = self.old(hashlib.sha256(split.encode()).hexdigest())
        self.assertTrue(audit.compared_with_earlier(old, self.now("text", audit.text_digest(joined)), self.URL,
                                                    split).startswith("the same as"))
        changed = audit.text_digest(joined.replace("699", "698"))
        self.assertTrue(audit.compared_with_earlier(old, self.now("text", changed), self.URL,
                                                    split).startswith("different from"))

    def test_without_the_old_text_it_is_not_known(self):
        said = audit.compared_with_earlier(self.old("abc"), self.now("text", "def"), self.URL, None)
        self.assertTrue(said.startswith("not known"))
        # Saved text that is not the text the old hash was taken from does not count.
        said = audit.compared_with_earlier(self.old("abc"), self.now("text", "def"), self.URL, "other words")
        self.assertTrue(said.startswith("not known"))

    def test_current_rules_hashes_are_compared_directly(self):
        self.assertTrue(audit.compared_with_earlier(self.old("abc", rules=audit.RULES), self.now("text", "abc"),
                                                    self.URL, None).startswith("the same as"))

    def test_nothing_to_say_without_an_earlier_hash_for_this_address(self):
        self.assertIsNone(audit.compared_with_earlier(None, self.now("text", "abc"), self.URL, None))
        self.assertIsNone(audit.compared_with_earlier(self.old("abc"), self.now("text", "abc"), "https://example.test/b", None))
        self.assertIsNone(audit.compared_with_earlier(self.old("abc"), {"state": audit.BLOCKED}, self.URL, None))


class RewriteRun(unittest.TestCase):
    """--write-baseline over an older baseline: what The Stasis Project's
    Nov. 16, 2026 recapture needed. A source it cannot read keeps its old hash;
    a source it can read says whether it says what the old hash said."""

    def test_a_rewrite_keeps_what_it_cannot_replace_and_says_what_changed(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        whole_pdf = b"%PDF-1.7\n" + b"x" * 200 + b"\n%%EOF\n"
        page = "<html><body><h1>Change a birth record</h1><p>" + ENOUGH + "</p></body></html>"
        bodies = {"same": page, "moved": page.replace("signed application", "notarized application")}
        old_text = "Change a birth record\n" + ENOUGH.replace(", ", ",\n")
        rules1 = hashlib.sha256(old_text.encode()).hexdigest()

        def old(source_id, digest, mode="text"):
            return {"id": source_id, "url": f"https://example.invalid/{source_id}", "fetched": "2026-11-15",
                    "state": "fetched", "mode": mode, "sha256": digest, "length": 1, "registry_checked": "2026-11-03"}
        before = {"same": old("same", rules1), "moved": old("moved", rules1), "refused": old("refused", rules1),
                  "pdf": old("pdf", hashlib.sha256(whole_pdf[:120]).hexdigest(), "bytes")}
        audit.save_baseline(tmp / "baseline.yml", list(before.values()))
        (tmp / "sources.yml").write_text(yaml.safe_dump([
            {"id": source_id, "url": f"https://example.invalid/{source_id}", "title": source_id, "checked": "2026-11-03"}
            for source_id in ("same", "moved", "refused", "pdf", "new")]), encoding="utf-8")
        for source_id in ("same", "moved", "refused"):
            audit.save_snapshot(tmp / "snapshots", source_id, old_text)

        def fetcher(url):
            name = url.rsplit("/", 1)[1]
            if name == "refused":
                return {"state": audit.BLOCKED, "note": "the site answered 403 to this tool"}
            if name == "pdf":
                return audit.examine(whole_pdf, "application/pdf", str(len(whole_pdf)))
            body = bodies.get(name, page).encode()
            return audit.examine(body, "text/html", str(len(body)))

        class Allow:
            def check(self, url):
                return True, None

        original = audit.fetch_all
        audit.fetch_all = lambda entries, **kw: original(entries, pause=0, host_pause=0, sleep=lambda s: None, **kw)
        self.addCleanup(setattr, audit, "fetch_all", original)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = audit.main(["--write-baseline", "--baseline", str(tmp / "baseline.yml"), "--registry",
                               str(tmp / "sources.yml"), "--snapshots", str(tmp / "snapshots"), "--today", "2026-11-17"],
                              fetcher=fetcher, robots=Allow())
        self.assertEqual(code, 0)
        after = audit.load_baseline(tmp / "baseline.yml")
        self.assertEqual(after["refused"], before["refused"])
        self.assertEqual(after["same"]["earlier"], "the same as the entry of 2026-11-15 (rules 1)")
        self.assertTrue(after["moved"]["earlier"].startswith("different from the entry of 2026-11-15"))
        self.assertTrue(after["pdf"]["earlier"].startswith("different from"))
        self.assertNotIn("earlier", after["new"])
        said = out.getvalue()
        self.assertIn("Kept the earlier hash for sources that could not be read this time: refused", said)
        self.assertIn("a person reads these before the new hash is relied on: moved, pdf", said)
        self.assertIn("A first hash, with no earlier one to compare (a person reads these first): new", said)


class OneSetOfRules(unittest.TestCase):
    """The comparison-rules block is the same in The Stasis Project and The Strand Project."""

    def test_the_block_is_the_shared_one(self):
        source = Path(audit.__file__).read_text(encoding="utf-8")
        begin = source.index("# ===========================================================================\n# The comparison rules (begin)")
        end = source.index("# The comparison rules (end)")
        block = source[begin:end]
        self.assertEqual(hashlib.sha256(block.encode("utf-8")).hexdigest(), RULES_BLOCK_SHA256,
                         "The comparison rules changed. Make the same change in the other project's audit, "
                         "raise RULES if a hash changes, and update RULES_BLOCK_SHA256 in both projects' tests.")


class StopsPartway(unittest.TestCase):
    """A server that announces a length, sends part of it, and closes. Python's
    read with a size limit returns the part without an error; the tool must
    not hash it."""

    @classmethod
    def setUpClass(cls):
        class Partway(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                body = b"<html><body><p>Where to send your verification</p>" + b"<p>More</p>" * 50
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body) * 3))
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True

        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Partway)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.shutdown)
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}/page"
        direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        cls.opener = staticmethod(lambda request: direct.open(request, timeout=10))

    def test_python_returns_the_part_without_an_error(self):
        with self.opener(urllib.request.Request(self.url)) as response:
            body = response.read(audit.MAX_BYTES + 1)
            self.assertLess(len(body), int(response.headers["Content-Length"]))

    def test_the_part_is_never_hashed(self):
        original, audit.PAUSE = audit.PAUSE, 0
        try:
            result = audit.fetch(self.url, opener=self.opener)
        finally:
            audit.PAUSE = original
        self.assertEqual(result["state"], audit.UNREACHABLE)
        self.assertIn("bytes it announced", result["note"])
        self.assertIn("asked twice", result["note"])
        self.assertNotIn("sha256", result)


class CarryForwardRun(unittest.TestCase):
    """--carry-forward re-hashes from saved text and fetches nothing."""

    def test_old_entries_are_carried_forward_from_their_saved_text(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        text, page = "Change a birth record\nThe fee is $35.\n" + ENOUGH, "One moment, please...\nPlease wait while your request is being verified..."

        def old(source_id, words):
            return {"id": source_id, "url": f"https://example.invalid/{source_id}", "fetched": "2026-11-15",
                    "state": "fetched", "mode": "text", "sha256": hashlib.sha256(words.encode()).hexdigest(),
                    "length": len(words), "registry_checked": "2026-11-03"}

        audit.save_baseline(tmp / "baseline.yml", [old("s1", text), old("s2", page)])
        (tmp / "sources.yml").write_text(yaml.safe_dump([
            {"id": source_id, "url": f"https://example.invalid/{source_id}", "title": source_id}
            for source_id in ("s1", "s2")]), encoding="utf-8")
        for source_id, words in (("s1", text), ("s2", page)):
            audit.save_snapshot(tmp / "snapshots", source_id, words)

        def no_fetch(url):
            raise AssertionError("nothing is fetched")

        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = audit.main(["--carry-forward", "--baseline", str(tmp / "baseline.yml"), "--registry",
                               str(tmp / "sources.yml"), "--snapshots", str(tmp / "snapshots"), "--today", "2026-11-16"],
                              fetcher=no_fetch)
        self.assertEqual(code, 0)
        written = audit.load_baseline(tmp / "baseline.yml")
        self.assertEqual((written["s1"]["rules"], written["s1"]["sha256"]), (audit.RULES, audit.text_digest(text)))
        self.assertEqual(written["s1"]["fetched"], "2026-11-15")
        self.assertNotIn("rules", written["s2"])
        self.assertIn("s2: not carried forward (the baseline text is not the source", out.getvalue())


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
            return self.send(200, served(fixture(name)))
        if self.path == "/changes":
            return self.send(200, served(fixture("page-before.html" if Handler.phase == "before" else "page-after.html")))
        if self.path == "/form.pdf":
            return self.send(200, fixture("form.pdf"), "application/pdf")
        if self.path == "/new":
            return self.send(200, served(b"<p>New source</p>"))
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
