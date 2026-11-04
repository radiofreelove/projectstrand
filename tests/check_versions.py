#!/usr/bin/env python3
"""
Check that the test tools' Playwright version is the same everywhere.

    python3 tests/check_versions.py

Playwright's version appears in three places: test-tools/requirements.txt (browser
checks), test-tools/package.json (axe-core check), and the axe job's container image in
.github/workflows/checks.yml, which ships the matching browser. Dependabot
updates the first two but not the container tag, and the axe job is
warning-only, so a mismatch could quietly stop axe-core from running. This
check fails (exit 1) on any mismatch, so the update cannot merge until all
three match. Standard library only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    found = {}
    req = re.search(r"^playwright==([0-9.]+)\s*$", (ROOT / "test-tools/requirements.txt").read_text(encoding="utf-8"), re.M)
    found["test-tools/requirements.txt"] = req.group(1) if req else None
    found["test-tools/package.json"] = json.loads((ROOT / "test-tools/package.json").read_text(encoding="utf-8")).get("devDependencies", {}).get("playwright")
    image = re.search(r"mcr\.microsoft\.com/playwright:v([0-9.]+)-", (ROOT / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8"))
    found["checks.yml container"] = image.group(1) if image else None
    versions = set(found.values())
    if None in versions or len(versions) != 1:
        print("Playwright versions differ or are missing:", file=sys.stderr)
        for where, version in found.items():
            print(f"  - {where}: {version}", file=sys.stderr)
        return 1
    print(f"Playwright {versions.pop()} everywhere: " + ", ".join(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
