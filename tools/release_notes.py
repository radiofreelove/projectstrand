#!/usr/bin/env python3
"""
Say what the next GitHub release should be called and what it should say.

    python3 tools/release_notes.py                  Print the tag, title, and notes.
    python3 tools/release_notes.py --field tag      Print one of: tag, title,
                                                    prerelease, body.
    python3 tools/release_notes.py --check          Fail if CHANGELOG.md has no
                                                    entry for the version in
                                                    data/site.yml.

The version comes from data/site.yml ("0.1.5-beta"), the same value every
page shows in its footer. The tag is that version with a "v" in front. The
notes are that version's entry in CHANGELOG.md, so a release never says
anything the changelog does not.

.github/workflows/release.yml runs this after the checks pass on main and
publishes the release if the tag does not exist yet. It mirrors the release
setup in The Stasis Project; before this tool, a person had to remember to
publish each release by hand.

Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = ROOT / "CHANGELOG.md"
SITE_YML = ROOT / "data" / "site.yml"
PRERELEASE_WORDS = ("alpha", "beta", "rc")


class ReleaseError(Exception):
    pass


def version() -> str:
    for line in SITE_YML.read_text(encoding="utf-8").splitlines():
        m = re.match(r'version:\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    raise ReleaseError("no version found in data/site.yml")


def entry(ver: str) -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    m = re.search(rf"^## {re.escape(ver)} \([^)]*\)\s*$", text, re.M)
    if not m:
        raise ReleaseError(f"CHANGELOG.md has no entry for {ver}")
    rest = text[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    return body.strip() + "\n"


def fields() -> dict[str, str]:
    ver = version()
    return {
        "tag": "v" + ver,
        "title": ver,
        "prerelease": "true" if any(w in ver for w in PRERELEASE_WORDS) else "false",
        "body": entry(ver),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", choices=["tag", "title", "prerelease", "body"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    try:
        f = fields()
    except ReleaseError as exc:
        print(f"release_notes: {exc}", file=sys.stderr)
        return 1
    if args.check:
        print(f"CHANGELOG.md has an entry for {version()}.")
        return 0
    if args.field:
        print(f[args.field], end="" if args.field == "body" else "\n")
    else:
        print(f"tag: {f['tag']}\ntitle: {f['title']}\nprerelease: {f['prerelease']}\n\n{f['body']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
