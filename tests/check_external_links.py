#!/usr/bin/env python3
"""Report whether each source URL in data/sources.yml still answers.

Run on a schedule. Some government sites block automated requests, so a
failure here means "a person should open this link," not "the link is dead."
Exit 1 if any link fails, so the scheduled check shows a warning.
"""
from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parent.parent / "data"
HEADERS = {"User-Agent": "TheStrandProject-linkcheck/0.1 (scheduled source check)"}


def check(url: str) -> str:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=20) as resp:
                return f"{resp.status}"
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405, 501}:
                continue
            return f"HTTP {exc.code}"
        except Exception as exc:  # timeouts, DNS, TLS
            if method == "HEAD":
                continue
            return f"error: {exc.__class__.__name__}"
    return "error"


def main() -> int:
    sources = yaml.safe_load((DATA / "sources.yml").read_text(encoding="utf-8"))
    bad = 0
    for s in sources:
        result = check(s["url"])
        ok = result.startswith("2") or result.startswith("3")
        bad += 0 if ok else 1
        print(f"{'ok  ' if ok else 'OPEN'} {result:>16}  {s['id']}  {s['url']}")
        time.sleep(1)  # be polite to small government servers
    print(f"\n{bad} link(s) need a person to open them.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
