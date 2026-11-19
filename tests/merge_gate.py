#!/usr/bin/env python3
"""The merge gate (Stage A): a pull request may not leave the offline
health vector worse than main's.

    python3 tests/merge_gate.py --base DIR --head DIR

computes tests/guards.py's offline health vector for two checkouts of
this repo and fails (exit 1) on any decrease. A decrease the owner has
accepted passes when the pull request body carries a line of the form:

    Accepted decrease: <measure>, <from> to <to>, because <reason>

The body reaches this script through the PR_BODY environment variable
(the checks workflow sets it) or --body-file. Exit 2 is a usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import guards  # noqa: E402

ACCEPTED = re.compile(r"^Accepted decrease:\s*([a-z_]+),\s*(\d+)\s+to\s+(\d+),\s*because\s+(.+)$",
                      re.MULTILINE)


def accepted_decreases(body: str) -> dict:
    return {m.group(1): (int(m.group(2)), int(m.group(3)), m.group(4).strip())
            for m in ACCEPTED.finditer(body or "")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True, help="a checkout of the base branch")
    parser.add_argument("--head", type=Path, required=True, help="a checkout of the pull request")
    parser.add_argument("--body-file", type=Path, help="the pull request body, as a file")
    args = parser.parse_args(argv)
    body = args.body_file.read_text(encoding="utf-8") if args.body_file else os.environ.get("PR_BODY", "")
    accepted = accepted_decreases(body)
    base, head = guards.health_vector(args.base), guards.health_vector(args.head)
    failed = False
    for measure in sorted(set(base) | set(head)):
        was, now = base.get(measure, 0), head.get(measure, 0)
        note = ""
        if now < was:
            ok = measure in accepted and accepted[measure][0] == was \
                and accepted[measure][1] == now and bool(accepted[measure][2])
            note = "accepted in the pull request body" if ok else "DECREASE, not accepted"
            failed = failed or not ok
        print(f"{measure}: {was} -> {now}" + (f"  ({note})" if note else ""))
    if failed:
        print("The merge gate failed: a health measure fell without an accepted decrease.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
