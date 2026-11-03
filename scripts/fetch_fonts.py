#!/usr/bin/env python3
"""Download the optional Atkinson Hyperlegible Next font files listed in fonts.lock.json.

- Pinned file (sha256 set): the download must match, or the script exits 1.
- Unpinned file (sha256 null): the file is saved and its sha256 is printed so a
  maintainer can pin it. See docs/decisions/ADR-0007-fonts.md.
- No network: the script exits 2 and the site falls back to system fonts.

Files go to static/fonts/ and are never committed.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "fonts.lock.json"
DEST = ROOT / "static" / "fonts"


def main() -> int:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    DEST.mkdir(parents=True, exist_ok=True)
    unpinned = []
    for f in lock["files"]:
        url = f"{lock['base_url']}{lock['package']}@{lock['version']}/{f['src']}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TheStrandProject-build/0.1"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
        except Exception as exc:  # network or HTTP error
            print(f"Could not download {url}: {exc}")
            return 2
        digest = hashlib.sha256(data).hexdigest()
        if f["sha256"] and f["sha256"] != digest:
            print(f"CHECKSUM MISMATCH for {f['src']}: expected {f['sha256']}, got {digest}")
            for other in lock["files"]:  # never ship a partial or tampered set
                (DEST / other["dest"]).unlink(missing_ok=True)
            return 1
        if not f["sha256"]:
            unpinned.append((f["src"], digest))
        (DEST / f["dest"]).write_bytes(data)
        print(f"ok  {f['dest']}  sha256={digest}")
    if unpinned:
        print("\nUNPINNED files. Add these sha256 values to fonts.lock.json, and set 'version' to the exact version:")
        for src, digest in unpinned:
            print(f"  {src}: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
