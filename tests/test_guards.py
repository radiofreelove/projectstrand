"""Stage A: the baseline guards, the ledgers, and the atomic writer.

The fixtures are small entry dicts in the shape the evidence audit uses.
The guard's promise is narrow and total: a baseline write that would
drop a hash, swap a hash unaccepted, weaken an entry, shrink coverage,
or move the written date backward is refused, and nothing is written.
"""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import guards  # noqa: E402

GUARDS_BLOCK_SHA256 = "a7b592cc159d3465b9ebc802ba638ca7066db49c5bb37098f70c5a6b49108685"

RULES = 2
REGISTRY = {"A": "https://x.test/a", "B": "https://x.test/b", "C": "https://x.test/c"}


def entry(source_id, sha="aaa", rules=RULES, state="fetched", mode="text", **extra):
    base = {"id": source_id, "url": REGISTRY[source_id], "fetched": "2026-11-17",
            "state": state, "mode": mode, "sha256": sha, "length": 3,
            "registry_checked": "2026-11-01"}
    if sha:
        base["rules"] = rules
    base.update(extra)
    return base


def blocked(source_id):
    return {"id": source_id, "url": REGISTRY[source_id], "fetched": "2026-11-17",
            "state": "checker-blocked", "mode": None, "sha256": None, "length": None,
            "registry_checked": "2026-11-01"}


OLD = {"A": entry("A"), "B": entry("B", sha="bbb"), "C": blocked("C")}


def check(new, **kw):
    return guards.check_invariants(OLD, new, REGISTRY, {}, "2026-11-17", "2026-11-18",
                                   RULES, kw.get("accepted", {}), kw.get("in_actions", False))


class Invariants(unittest.TestCase):
    def test_an_unchanged_write_passes(self):
        self.assertEqual(check(dict(OLD)), [])

    def test_b1_a_dropped_hash_is_refused(self):
        new = dict(OLD)
        new["A"] = blocked("A")
        self.assertTrue(any("B1" in r and r.startswith("A") for r in check(new)))

    def test_b1_a_missing_entry_with_a_hash_is_refused(self):
        new = {k: v for k, v in OLD.items() if k != "A"}
        self.assertTrue(any("B1" in r for r in check(new)))

    def test_b1_a_retired_entry_keeps_its_hash(self):
        new = {k: v for k, v in OLD.items() if k != "A"}
        retired = {"A": OLD["A"]}
        registry = {k: v for k, v in REGISTRY.items() if k != "A"}
        reasons = guards.check_invariants(OLD, new, registry, retired, "2026-11-17",
                                          "2026-11-18", RULES, {}, False)
        self.assertEqual(reasons, [])

    def test_b2_a_changed_hash_needs_acceptance(self):
        new = dict(OLD)
        new["A"] = entry("A", sha="zzz")
        self.assertTrue(any("B2" in r for r in check(new)))
        self.assertEqual(check(new, accepted={"A": "the letter was reissued"}), [])

    def test_b2_acceptance_is_refused_in_actions(self):
        new = dict(OLD)
        new["A"] = entry("A", sha="zzz")
        reasons = check(new, accepted={"A": "the letter was reissued"}, in_actions=True)
        self.assertTrue(any("B2" in r for r in reasons))

    def test_b2_a_rules_upgrade_rehash_is_not_a_change_of_content(self):
        old = {"A": entry("A", rules=1), "B": OLD["B"], "C": OLD["C"]}
        new = dict(old)
        new["A"] = entry("A", sha="rehashed", carried="re-hashed under rules 2")
        reasons = guards.check_invariants(old, new, REGISTRY, {}, "2026-11-17",
                                          "2026-11-18", RULES, {}, False)
        self.assertEqual(reasons, [])

    def test_b3_a_rules_downgrade_is_refused(self):
        new = dict(OLD)
        new["A"] = entry("A", rules=1)
        self.assertTrue(any("B3" in r for r in check(new)))

    def test_b3_a_mode_change_is_refused(self):
        new = dict(OLD)
        new["A"] = entry("A", mode="bytes")
        self.assertTrue(any("B3" in r for r in check(new)))

    def test_b3_an_earlier_result_dropped_is_refused(self):
        old = dict(OLD)
        old["A"] = entry("A", earlier="the same as the entry of 2026-11-15 (rules 2)")
        new = dict(old)
        new["A"] = entry("A")
        reasons = guards.check_invariants(old, new, REGISTRY, {}, "2026-11-17",
                                          "2026-11-18", RULES, {}, False)
        self.assertTrue(any("B3" in r for r in reasons))

    def test_b3_registry_checked_never_moves_backward(self):
        new = dict(OLD)
        new["A"] = entry("A", registry_checked="2026-10-01")
        self.assertTrue(any("B3" in r for r in check(new)))

    def test_b4_coverage_never_shrinks(self):
        new = dict(OLD)
        new["B"] = blocked("B")
        self.assertTrue(any("B4" in r for r in check(new)))

    def test_b5_the_written_date_never_moves_backward(self):
        reasons = guards.check_invariants(OLD, dict(OLD), REGISTRY, {}, "2026-11-17",
                                          "2026-11-16", RULES, {}, False)
        self.assertTrue(any("B5" in r for r in reasons))


class CompletenessDiff(unittest.TestCase):
    def test_a_no_op_write_reports_none(self):
        lines = guards.completeness_diff(OLD, dict(OLD), {}, RULES, "Test", "2026-11-18")
        text = "\n".join(lines)
        self.assertIn("gained: none", text)
        self.assertIn("lost: none", text)
        self.assertIn("hash changed: none", text)
        self.assertIn("entries: 3 -> 3", text)

    def test_a_first_hash_is_a_gain(self):
        new = dict(OLD)
        new["C"] = entry("C", sha="ccc")
        text = "\n".join(guards.completeness_diff(OLD, new, {}, RULES, "Test", "2026-11-18"))
        self.assertIn("gained: C", text)
        self.assertIn("hashed under rules 2: 2 -> 3", text)


class Ledgers(unittest.TestCase):
    def test_ledger1_closes(self):
        line, reasons = guards.ledger1(REGISTRY, OLD, set(), RULES)
        self.assertEqual(line, "3 = 2 + 0 + 1 + 0")
        self.assertEqual(reasons, [])

    def test_ledger1_names_a_missing_entry(self):
        entries = {k: v for k, v in OLD.items() if k != "B"}
        _, reasons = guards.ledger1(REGISTRY, entries, set(), RULES)
        self.assertTrue(any(r.startswith("B") for r in reasons))

    def test_ledger2_names_an_omitted_source(self):
        states = {"A": "unchanged", "C": "checker-blocked"}
        reasons = guards.ledger2(REGISTRY, states, OLD, RULES)
        self.assertTrue(any("no result for: B" in r for r in reasons))

    def test_ledger2_closes_on_a_consistent_run(self):
        states = {"A": "unchanged", "B": "changed", "C": "checker-blocked"}
        self.assertEqual(guards.ledger2(REGISTRY, states, OLD, RULES), [])

    def test_ledger2_catches_a_compared_source_with_no_hash(self):
        states = {"A": "unchanged", "B": "unchanged", "C": "unchanged"}
        reasons = guards.ledger2(REGISTRY, states, OLD, RULES)
        self.assertTrue(any(r.startswith("C") for r in reasons))

    def test_ledger3_names_a_cited_source_outside_the_registry(self):
        reasons = guards.ledger3_cited({"A", "ZZ"}, set(REGISTRY))
        self.assertTrue(any("ZZ" in r for r in reasons))


class AtomicWrite(unittest.TestCase):
    def test_a_write_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.yml"
            path.write_text("- id: A\n", encoding="utf-8")
            guards.atomic_write(path, "- id: A\n- id: B\n",
                                guards.parse_baseline_text, [{"id": "A"}, {"id": "B"}])
            self.assertEqual(guards.parse_baseline_text(path.read_text(encoding="utf-8")),
                             [{"id": "A"}, {"id": "B"}])

    def test_a_killed_write_leaves_the_original_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.yml"
            original = "- id: A\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                guards.atomic_write(path, "- id: B\n", guards.parse_baseline_text,
                                    [{"id": "B"}], fail_after_temp=True)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_a_round_trip_mismatch_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.yml"
            original = "- id: A\n"
            path.write_text(original, encoding="utf-8")
            with self.assertRaises(ValueError):
                guards.atomic_write(path, "- id: B\n",
                                    guards.parse_baseline_text, [{"id": "A"}])
            self.assertEqual(path.read_text(encoding="utf-8"), original)


class GuardedSave(unittest.TestCase):
    """The audit's own write path: a tampered write is refused, exit 3,
    and the baseline on disk is untouched."""

    def test_a_write_with_one_hash_removed_is_refused(self):
        import evidence_audit as audit
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.yml"
            entries = [OLD["A"], OLD["B"], OLD["C"]]
            audit.save_baseline(path, entries, "2026-11-17")
            before = path.read_bytes()
            tampered = [dict(e) for e in entries]
            tampered[0]["sha256"] = None
            ok = audit.save_baseline_guarded(path, tampered, "2026-11-18",
                                             {e["id"]: e for e in entries},
                                             [{"id": i, "url": u} for i, u in REGISTRY.items()], {})
            self.assertFalse(ok)
            self.assertEqual(path.read_bytes(), before)

    def test_a_clean_write_stamps_the_written_date(self):
        import evidence_audit as audit
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.yml"
            entries = [OLD["A"], OLD["B"], OLD["C"]]
            audit.save_baseline(path, entries, "2026-11-17")
            ok = audit.save_baseline_guarded(path, [dict(e) for e in entries], "2026-11-18",
                                             {e["id"]: e for e in entries},
                                             [{"id": i, "url": u} for i, u in REGISTRY.items()], {})
            self.assertTrue(ok)
            _, written, _ = guards.load_baseline_file(path)
            self.assertEqual(written, "2026-11-18")


class GuardedRunEndToEnd(unittest.TestCase):
    """The whole tool against a local server whose page changes: a
    baseline refresh that would swap the hash is refused (exit 3) until
    a person accepts the change, and acceptance is refused outright
    when GITHUB_ACTIONS is set."""

    BODY = ("<html><body><p>To change the sex on a birth record, send the signed "
            "application, a copy of your photo ID, and the fee to the state vital "
            "records office. You do not need a court order or a letter from a "
            "doctor. A parent or guardian signs for a minor. The office mails "
            "the new certificate, and the old one is sealed. The fee is $%d.</p>"
            "</body></html>")

    @classmethod
    def setUpClass(cls):
        import http.server
        import threading

        class Handler(http.server.BaseHTTPRequestHandler):
            fee = 35

            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/robots.txt":
                    body = b"User-agent: *\nAllow: /\n"
                else:
                    body = (GuardedRunEndToEnd.BODY % Handler.fee).encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        cls.handler = Handler
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.addClassCleanup(cls.server.shutdown)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"

    def setUp(self):
        import evidence_audit as audit
        self.audit = audit
        self.pauses = (audit.PAUSE, audit.HOST_PAUSE)
        audit.PAUSE = audit.HOST_PAUSE = 0.0
        self.addCleanup(setattr, audit, "PAUSE", self.pauses[0])
        self.addCleanup(setattr, audit, "HOST_PAUSE", self.pauses[1])
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.tmp, ignore_errors=True))
        (self.tmp / "sources.yml").write_text(
            f"- id: one\n  title: \"One\"\n  url: {self.base}/page\n  checked: 2026-11-01\n")
        self.handler.fee = 35
        os.environ.pop("GITHUB_ACTIONS", None)

    def run_tool(self, *extra):
        import contextlib
        import io
        args = ["--registry", str(self.tmp / "sources.yml"),
                "--baseline", str(self.tmp / "baseline.yml"),
                "--snapshots", str(self.tmp / "snap"), "--today", "2026-11-18", *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = self.audit.main(args)
        return code

    def test_a_changed_hash_needs_a_persons_acceptance(self):
        self.assertEqual(self.run_tool("--write-baseline"), 0)
        before = (self.tmp / "baseline.yml").read_bytes()
        self.handler.fee = 40
        self.assertEqual(self.run_tool("--write-baseline"), 3)
        self.assertEqual((self.tmp / "baseline.yml").read_bytes(), before)
        self.assertEqual(self.run_tool("--write-baseline", "--accept-change", "one",
                                       "--reason", "the fee rose; read on the page"), 0)
        self.handler.fee = 45
        os.environ["GITHUB_ACTIONS"] = "true"
        try:
            self.assertEqual(self.run_tool("--write-baseline", "--accept-change", "one",
                                           "--reason", "the fee rose again"), 3)
        finally:
            os.environ.pop("GITHUB_ACTIONS", None)


class OneSetOfGuards(unittest.TestCase):
    """The guards block is the same in The Strand Project and The Stasis Project."""

    def test_the_block_is_the_shared_one(self):
        source = Path(guards.__file__).read_text(encoding="utf-8")
        begin = source.index("# ===========================================================================\n# The baseline guards (begin)")
        end = source.index("# The baseline guards (end)")
        block = source[begin:end]
        self.assertEqual(hashlib.sha256(block.encode("utf-8")).hexdigest(), GUARDS_BLOCK_SHA256,
                         "The baseline guards changed. Make the same change in the other "
                         "project's guards, and update GUARDS_BLOCK_SHA256 in both projects' tests.")


if __name__ == "__main__":
    unittest.main()
