#!/usr/bin/env python3
"""List sources that are due for a re-check.

A source is due when its "checked" date in data/sources.yml is older than
max_source_age_days in data/site.yml. Exit 1 if any are due, so the checks
show a warning. Re-check the source, then update its "checked" date and the
page's "checked" date in data/pages.yml, and log it in docs/AUDIT-LOG.md.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PUBLIC = ROOT / "public"


def main() -> int:
    site = yaml.safe_load((DATA / "site.yml").read_text(encoding="utf-8"))
    sources = yaml.safe_load((DATA / "sources.yml").read_text(encoding="utf-8"))
    pages = yaml.safe_load((DATA / "pages.yml").read_text(encoding="utf-8"))
    limit = int(site.get("max_source_age_days", 120))
    today = dt.date.today()
    due = []
    source_dates = {}
    for s in sources:
        d = dt.date.fromisoformat(str(s["checked"]))
        source_dates[s["id"]] = d
        age = (today - d).days
        if age > limit:
            due.append((age, s["id"], s["url"]))
    for p in pages:
        age = (today - dt.date.fromisoformat(str(p["checked"]))).days
        if age > limit:
            due.append((age, f"page:{p['slug']}", ""))

    mismatches = []
    report_path = PUBLIC / "build-report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for p in report.get("pages", []):
            p_date = dt.date.fromisoformat(str(p["checked"]))
            cited = [source_dates[sid] for sid in p.get("sources", []) if sid in source_dates]
            if cited and p_date < max(cited):
                mismatches.append(f"page:{p['slug']} ({p_date}) lags behind cited source ({max(cited)})")

    if not due and not mismatches:
        print(f"All sources and pages checked within {limit} days, and no page lags behind its cited sources.")
        return 0
    if due:
        print(f"{len(due)} item(s) are due for a re-check (limit {limit} days):")
        for age, sid, url in sorted(due, reverse=True):
            print(f"  {age:4d} days  {sid}  {url}")
    if mismatches:
        print(f"{len(mismatches)} page checked date mismatch(es):")
        for item in mismatches:
            print(f"  {item}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
