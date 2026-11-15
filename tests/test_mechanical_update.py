#!/usr/bin/env python3
"""
Tests for tests/mechanical_update.py: it may move a "checked" date only
for a source the evidence audit verified as unchanged, and nothing else.

    python3 tests/test_mechanical_update.py

Each test works on a copy of data/sources.yml in a temporary folder, with
a made-up audit and baseline. The real data/sources.yml is never written.
No network. Fails (exit 1) if any test fails. Needs PyYAML.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import mechanical_update as mech  # noqa: E402

REAL = HERE.parent / "data" / "sources.yml"
TODAY = "2026-11-16"
HASH = "a" * 64


class Gating(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.registry = self.tmp / "sources.yml"
        shutil.copy(REAL, self.registry)
        self.sources = {s["id"]: s for s in yaml.safe_load(self.registry.read_text())}
        # One source in each state. Their baselines all hold a hash.
        self.states = {
            "or-oha-gender": "unchanged",
            "ut-courts-fees": "unchanged",
            "wa-doh-sex": "changed",
            "us-state-sex-marker": "checker-blocked",
            "brand-odhs": "unreachable",
            "or-ojd-forms": "not yet baselined",
        }
        self.write_baseline({sid: HASH for sid in self.states})
        self.write_audit()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_baseline(self, hashes: dict):
        entries = [{"id": sid, "url": self.sources[sid]["url"], "fetched": dt.date(2026, 11, 15),
                    "state": "fetched", "mode": "text", **({"sha256": h} if h else {})}
                   for sid, h in hashes.items()]
        (self.tmp / "baseline.yml").write_text(yaml.safe_dump(entries, sort_keys=False))

    def write_audit(self, date=TODAY, extra=(), override=None):
        results = [{"id": sid, "url": self.sources[sid]["url"], "state": state,
                    "sha256": HASH if state in ("unchanged", "changed") else None}
                   for sid, state in self.states.items()]
        for result in results:
            result.update((override or {}).get(result["id"], {}))
        results += list(extra)
        (self.tmp / "audit.json").write_text(json.dumps({"audit_date": date, "results": results}))

    def run_tool(self, *extra):
        out, err = io.StringIO(), io.StringIO()
        args = ["--audit", str(self.tmp / "audit.json"), "--registry", str(self.registry),
                "--baseline", str(self.tmp / "baseline.yml"), "--today", TODAY, *extra]
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mech.main(args)
        return code, out.getvalue(), err.getvalue()

    def changed_lines(self):
        old, new = REAL.read_text().split("\n"), self.registry.read_text().split("\n")
        self.assertEqual(len(old), len(new))
        return [(a, b) for a, b in zip(old, new) if a != b]

    def test_only_unchanged_sources_move_and_nothing_else_changes(self):
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(self.changed_lines(), [("  checked: 2026-11-03", "  checked: 2026-11-16")] * 2)
        after = {s["id"]: s for s in yaml.safe_load(self.registry.read_text())}
        for sid, src in self.sources.items():
            expected = dict(src)
            if sid in ("or-oha-gender", "ut-courts-fees"):
                expected["checked"] = dt.date(2026, 11, 16)
            self.assertEqual(after[sid], expected, sid)
        self.assertIn("- or-oha-gender: 2026-11-03 to 2026-11-16", out)
        self.assertIn("- ut-courts-fees: 2026-11-03 to 2026-11-16", out)
        self.assertIn("2 checked dates updated", out)
        for sid in ("wa-doh-sex", "us-state-sex-marker", "brand-odhs", "or-ojd-forms"):
            self.assertNotIn(sid, out)
        # Comments and layout are kept.
        self.assertIn("# status:\n#   verified    We opened and read it", self.registry.read_text())

    def test_refuses_to_touch_a_changed_blocked_unreachable_or_unbaselined_source(self):
        for sid in ("wa-doh-sex", "us-state-sex-marker", "brand-odhs", "or-ojd-forms", "or-lawhelp"):
            code, _, err = self.run_tool("--only", sid)
            self.assertEqual(code, 2, sid)
            self.assertIn("Refused. Nothing was written.", err)
            self.assertEqual(self.registry.read_text(), REAL.read_text(), sid)
        # One bad source in --only refuses the whole run, including the good one.
        code, _, err = self.run_tool("--only", "or-oha-gender", "wa-doh-sex")
        self.assertEqual(code, 2)
        self.assertIn("wa-doh-sex: the audit says changed", err)
        self.assertEqual(self.registry.read_text(), REAL.read_text())

    def test_only_limits_the_run(self):
        code, out, _ = self.run_tool("--only", "ut-courts-fees")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.changed_lines()), 1)
        self.assertNotIn("or-oha-gender", out)

    def test_hash_must_match_the_baseline(self):
        self.write_audit(override={"or-oha-gender": {"sha256": "b" * 64}})
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("or-oha-gender: the audit's hash is not the baseline's hash", err)
        self.assertEqual(self.registry.read_text(), REAL.read_text())

    def test_baseline_must_hold_a_hash(self):
        self.write_baseline({"or-oha-gender": None, "ut-courts-fees": HASH})
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("baseline holds no hash", err)

    def test_address_must_agree_everywhere(self):
        self.write_audit(override={"ut-courts-fees": {"url": "https://example.test/moved"}})
        code, _, err = self.run_tool()
        self.assertEqual(code, 2)
        self.assertIn("do not name one address", err)

    def test_stale_future_duplicate_and_unknown_audits_are_refused(self):
        for kwargs, words in (
            ({"date": "2026-11-10"}, "more than 2 days ago"),
            ({"date": "2026-11-20"}, "after today"),
            ({"date": "soon"}, "no 'audit_date'"),
            ({"extra": [{"id": "or-oha-gender", "url": "x", "state": "unchanged"}]}, "listed twice"),
            ({"extra": [{"id": "or-lawhelp", "url": "x", "state": "probably fine"}]}, "unknown state"),
            ({"extra": [{"id": "not-a-source", "url": "x", "state": "unchanged", "sha256": HASH}]},
             "unchanged in the audit, but"),
        ):
            self.write_audit(**kwargs)
            code, _, err = self.run_tool()
            self.assertEqual(code, 2, words)
            self.assertIn(words, err)
            self.assertEqual(self.registry.read_text(), REAL.read_text(), words)

    def test_a_date_never_moves_backward(self):
        self.states = {"wa-dol-gender": "unchanged"}  # checked 2026-11-14
        self.write_baseline({"wa-dol-gender": HASH})
        self.write_audit(date="2026-11-14")
        code, out, _ = self.run_tool()
        self.assertEqual(code, 0)
        self.assertIn("wa-dol-gender: already checked on 2026-11-14", out)
        self.assertEqual(self.registry.read_text(), REAL.read_text())

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_tool("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Dry run", out)
        self.assertIn("2 checked dates would be updated", out)
        self.assertIn("or-oha-gender: 2026-11-03 to 2026-11-16", out)
        self.assertEqual(self.registry.read_text(), REAL.read_text())

    def test_the_edit_check_catches_a_stray_change(self):
        text = REAL.read_text()
        with self.assertRaises(mech.Refused):
            mech.apply(text, [("or-oha-gender", "2026-11-03", "2026-11-16"),
                              ("or-oha-gender", "2026-11-16", "2026-11-17")])


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=1).result
    sys.exit(0 if result.wasSuccessful() else 1)
