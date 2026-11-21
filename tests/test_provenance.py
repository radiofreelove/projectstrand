#!/usr/bin/env python3
"""Unit checks for Strand's provenance features:
- collapsible 'What these labels mean' key on every badged content page
- two-date source rendering ('Date on it:' + 'Checked:') on /sources and page source lists
- plain-language human vs. automated check distinction on /about
- auto-generated docs/claims.md stays in sync with data/facts.yml and data/sources.yml
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "public"
DOCS = ROOT / "docs"

sys.path.insert(0, str(ROOT))
import build  # noqa: E402


class ProvenanceChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (PUBLIC / "build-report.json").exists():
            rc = build.main()
            assert rc == 0
        cls.report = json.loads((PUBLIC / "build-report.json").read_text(encoding="utf-8"))
        cls.sources_json = json.loads((PUBLIC / "sources.json").read_text(encoding="utf-8"))

    def test_badged_pages_have_collapsible_label_key(self):
        for page in self.report["pages"]:
            slug = page["slug"]
            html = (PUBLIC / f"{slug}.html").read_text(encoding="utf-8")
            if page["badges"] and slug not in {"sources", "about", "404"}:
                self.assertIn('<details class="label-key">', html, slug)
                self.assertIn("<summary>What these labels mean</summary>", html, slug)
            else:
                self.assertNotIn('<details class="label-key">', html, slug)

    def test_two_date_sources_render_on_sources_and_content_pages(self):
        sources_html = (PUBLIC / "sources.html").read_text(encoding="utf-8")
        self.assertIn("Date on it:", sources_html)
        self.assertIn("Checked: <time datetime=", sources_html)
        for slug in ("oregon", "washington", "utah", "compare"):
            html = (PUBLIC / f"{slug}.html").read_text(encoding="utf-8")
            self.assertIn("Date on it:", html, slug)
            self.assertIn("Checked: <time datetime=", html, slug)
        self.assertTrue(all("document_date" in s for s in self.sources_json))
        self.assertTrue(all("internal_note" not in s for s in self.sources_json))

    def test_about_page_distinguishes_automated_checks_from_human_review(self):
        about_html = (PUBLIC / "about.html").read_text(encoding="utf-8")
        self.assertIn("A computer checks every week", about_html)
        self.assertIn("A person reviews and updates the guide", about_html)
        self.assertIn("public filing cabinet", about_html)
        self.assertIn("docs/claims.md", about_html)

    def test_claims_md_matches_current_data(self):
        sources_list = build.load_yaml("sources.yml")
        sources = {s["id"]: {**s, "document_date": build.source_document_date(s)} for s in sources_list}
        facts = build.load_yaml("facts.yml")
        expected = build.render_claims_md(facts, sources, self.report["pages"])
        claims_path = DOCS / "claims.md"
        self.assertTrue(claims_path.exists(), "docs/claims.md should exist")
        self.assertEqual(claims_path.read_text(encoding="utf-8"), expected)


if __name__ == "__main__":
    unittest.main()
