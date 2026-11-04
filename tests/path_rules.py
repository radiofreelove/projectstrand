#!/usr/bin/env python3
"""
Check the path finder's routing rules in templates/pages/path.html.j2.

    python3 tests/path_rules.py

Every answer to "What do you want to change?" is tried with every answer to
"Who is this for?", for every result block. Fails (exit 1) if:

  1. A line shows for "Name" or for "Gender marker" but not for "Both".
     "Both" covers both changes, so it must show everything either one shows.
     Exception: Oregon court (t-court-or), where one petition covers both,
     so "Both" has its own line instead. See docs/PATH-LOGIC.md.
  2. A line uses a data-change or data-who value the questions do not offer.
  3. path.js asks for a block that the template does not define.

Standard library only. Added after two "Both" gaps were found on
2026-11-03 (docs/AUDIT-LOG.md).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "templates" / "pages" / "path.html.j2"
SCRIPT = ROOT / "static" / "js" / "path.js"

CHANGES = ("name", "marker", "both")
WHO = ("adult", "parent", "minor")
LIVE = ("or", "wa", "ut", "other")
BORN = ("or", "wa", "ut", "other-us", "outside")
BOTH_HAS_OWN_LINE = {"t-court-or"}


def strip(text: str) -> str:
    text = re.sub(r"\{\{.*?\}\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split())[:80]


def main() -> int:
    template = TEMPLATE.read_text(encoding="utf-8")
    blocks = dict(re.findall(r'<template id="(t-[a-z-]+)">(.*?)</template>', template, re.S))
    errors = []

    lines = {}
    for block_id, body in blocks.items():
        lines[block_id] = []
        for attrs, text in re.findall(r"<li([^>]*)>(.*?)</li>", body, re.S):
            change = re.search(r'data-change="([^"]+)"', attrs)
            who = re.search(r'data-who="([^"]+)"', attrs)
            change = change.group(1).split() if change else None
            who = who.group(1).split() if who else None
            for value in change or []:
                if value not in CHANGES:
                    errors.append(f"{block_id}: unknown data-change value '{value}' on: {strip(text)}")
            for value in who or []:
                if value not in WHO:
                    errors.append(f"{block_id}: unknown data-who value '{value}' on: {strip(text)}")
            lines[block_id].append((change, who, strip(text)))

    def shown(block_id: str, change: str, who: str) -> set[str]:
        return {
            text for c, w, text in lines[block_id]
            if (c is None or change in c) and (w is None or who in w)
        }

    for block_id in sorted(blocks):
        if block_id in BOTH_HAS_OWN_LINE:
            continue
        for who in WHO:
            missing = (shown(block_id, "name", who) | shown(block_id, "marker", who)) - shown(block_id, "both", who)
            for text in sorted(missing):
                errors.append(f"{block_id}, who={who}: shows for name or marker but not both: {text}")

    script = SCRIPT.read_text(encoding="utf-8")
    wanted = {"t-federal", "t-after"}
    for prefix, answers in (("t-court-", LIVE), ("t-id-", LIVE), ("t-birth-", BORN), ("t-help-", LIVE)):
        if f'"{prefix}" + answers.' not in script:
            errors.append(f"path.js no longer builds block names from '{prefix}'; update this test")
        wanted.update(prefix + answer for answer in answers)
    for block_id in sorted(wanted - set(blocks)):
        errors.append(f"path.js can ask for {block_id}, but the template does not define it")

    if errors:
        print("Path finder rules:\n  - " + "\n  - ".join(errors), file=sys.stderr)
        return 1
    combos = len(LIVE) * len(CHANGES) * len(WHO) * len(BORN)
    print(f"Path finder rules pass: {len(blocks)} blocks, {combos} answer combinations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
