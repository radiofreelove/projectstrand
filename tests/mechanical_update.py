#!/usr/bin/env python3
"""
Draft the "checked" date updates an evidence audit run has proved.

    python3 tests/evidence_audit.py --report evidence-report.md --results evidence-results.json
    python3 tests/mechanical_update.py --audit evidence-results.json

For every source the audit found unchanged, this sets the source's
"checked" date in data/sources.yml to the day of the audit. The proof is
the hash match: the source returned the same content as its baseline in
data/evidence_baseline.yml. It changes nothing else: no other field, no
other source, no other file. It prints every date it changed.

A date set this way means "a tool found the same content as the last
verified check", not "a person read it again". It is draft-only: run it
on a branch and review the diff before anything merges. It is not wired
into the weekly workflow (docs/OPERATIONS.md, "Mechanical date updates").

It refuses to write anything, and exits with code 2, if:

  - a source named with --only is not "unchanged" in the audit (changed,
    checker-blocked, unreachable, not yet baselined, or missing);
  - a source the audit calls unchanged does not match the baseline: a
    different hash, a different address, or no stored hash;
  - a source the audit calls unchanged is not in data/sources.yml, or its
    address there is different;
  - the audit lists a source twice, names a state this tool does not
    know, or is more than MAX_AGE_DAYS days old or dated in the future;
  - the edit would change anything in data/sources.yml other than those
    "checked" lines.

An unchanged source whose "checked" date is already the audit's date or
later is left alone and listed. A date never moves backward.

--dry-run prints the summary and writes nothing. Needs PyYAML.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "sources.yml"
BASELINE = ROOT / "data" / "evidence_baseline.yml"

UNCHANGED = "unchanged"
STATES = {UNCHANGED, "changed", "unreachable", "checker-blocked", "not yet baselined"}
# An audit older than this proves nothing about today.
MAX_AGE_DAYS = 2
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


class Refused(Exception):
    """The audit does not prove what this tool would write."""


def iso(value) -> str:
    return value.isoformat()[:10] if isinstance(value, (dt.date, dt.datetime)) else str(value)


def plan(audit: dict, registry: list, baseline: list, today: str, only=None):
    """Work out the updates. Returns (updates, left_alone).

    updates: [(source id, old date, new date)]. left_alone: [(id, why)].
    Raises Refused, with every reason, if the audit cannot be trusted for
    any source this run would touch.
    """
    problems = []
    audit_date = audit.get("audit_date", "")
    if not isinstance(audit_date, str) or not DATE_RE.fullmatch(audit_date):
        raise Refused("the audit has no 'audit_date' like 2026-11-16")
    age = (dt.date.fromisoformat(today) - dt.date.fromisoformat(audit_date)).days
    if age < 0:
        problems.append(f"the audit is dated {audit_date}, after today ({today})")
    elif age > MAX_AGE_DAYS:
        problems.append(f"the audit is from {audit_date}, more than {MAX_AGE_DAYS} days ago; run it again")

    results: dict[str, dict] = {}
    for result in audit.get("results", []):
        source_id = result.get("id")
        if source_id in results:
            problems.append(f"{source_id}: listed twice in the audit")
        if result.get("state") not in STATES:
            problems.append(f"{source_id}: unknown state {result.get('state')!r}")
        results[source_id] = result

    by_id = {src["id"]: src for src in registry}
    base = {entry["id"]: entry for entry in (baseline or [])}
    if only:
        wanted = list(dict.fromkeys(only))
        for source_id in wanted:
            state = results.get(source_id, {}).get("state", "not in the audit")
            if state != UNCHANGED:
                problems.append(f"{source_id}: the audit says {state}, so its date cannot be updated")
    else:
        wanted = [source_id for source_id, result in results.items() if result.get("state") == UNCHANGED]

    updates, left_alone = [], []
    for source_id in wanted:
        result = results.get(source_id)
        if not result or result.get("state") != UNCHANGED:
            continue  # already reported above
        src, entry = by_id.get(source_id), base.get(source_id)
        if src is None:
            problems.append(f"{source_id}: unchanged in the audit, but not in data/sources.yml")
            continue
        if not entry or not entry.get("sha256"):
            problems.append(f"{source_id}: unchanged in the audit, but the baseline holds no hash for it")
            continue
        if result.get("sha256") != entry["sha256"]:
            problems.append(f"{source_id}: the audit's hash is not the baseline's hash")
            continue
        if not (result.get("url") == entry.get("url") == src["url"]):
            problems.append(f"{source_id}: the audit, the baseline, and data/sources.yml do not name one address")
            continue
        old = iso(src["checked"])
        if old >= audit_date:
            left_alone.append((source_id, f"already checked on {old}"))
        else:
            updates.append((source_id, old, audit_date))

    if problems:
        raise Refused("\n  - ".join(problems))
    return updates, left_alone


def apply(text: str, updates) -> str:
    """Change only the "checked" lines of the named sources in the file's
    text, so comments, layout, and every other character stay as they
    were. Confirms the result by reading both versions back."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if re.match(r"- id:\s*", line)]
    for source_id, old, new in updates:
        found = [i for i in starts if re.fullmatch(r"- id:\s*['\"]?" + re.escape(source_id) + r"['\"]?\s*", lines[i])]
        if len(found) != 1:
            raise Refused(f"{source_id}: could not find exactly one entry for it in data/sources.yml")
        start = found[0]
        end = next((i for i in starts if i > start), len(lines))
        hits = [i for i in range(start, end)
                if re.fullmatch(r"  checked:\s*['\"]?" + re.escape(old) + r"['\"]?\s*", lines[i])]
        if len(hits) != 1:
            raise Refused(f"{source_id}: could not find its 'checked: {old}' line in data/sources.yml")
        lines[hits[0]] = lines[hits[0]].replace(old, new)
    new_text = "\n".join(lines)

    before, after = yaml.safe_load(text), yaml.safe_load(new_text)
    dates = {source_id: new for source_id, _, new in updates}
    expected = []
    for src in before:
        src = dict(src)
        if src["id"] in dates:
            src["checked"] = dt.date.fromisoformat(dates[src["id"]])
        expected.append(src)
    changed_lines = sum(1 for a, b in zip(text.split("\n"), new_text.split("\n")) if a != b)
    if after != expected or len(text.split("\n")) != len(new_text.split("\n")) or changed_lines != len(updates):
        raise Refused("the edit would change more than the 'checked' dates; nothing was written")
    return new_text


def summary(updates, left_alone, audit_date: str, dry_run: bool = False) -> str:
    verb = "would be updated" if dry_run else "updated"
    lines = [f"Evidence audit of {audit_date}: {len(updates)} checked dates {verb} in data/sources.yml.", ""]
    lines += [f"- {source_id}: {old} to {new}" for source_id, old, new in updates]
    if left_alone:
        lines += ["", f"Unchanged in the audit and left alone ({len(left_alone)}):", ""]
        lines += [f"- {source_id}: {why}" for source_id, why in left_alone]
    lines += ["", "Each date means a tool found the same content as the baseline, not that a person read the source again."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audit", type=Path, required=True,
                        help="the JSON file tests/evidence_audit.py wrote with --results")
    parser.add_argument("--only", nargs="+", metavar="ID", help="only these source ids")
    parser.add_argument("--registry", type=Path, default=REGISTRY, help="the sources file to update (for tests)")
    parser.add_argument("--baseline", type=Path, default=BASELINE, help="the baseline file (for tests)")
    parser.add_argument("--summary", type=Path, help="also write the summary to this file")
    parser.add_argument("--dry-run", action="store_true", help="print the summary; write nothing")
    parser.add_argument("--today", help="YYYY-MM-DD, for testing")
    args = parser.parse_args(argv)
    today = args.today or dt.date.today().isoformat()

    try:
        audit = json.loads(args.audit.read_text(encoding="utf-8"))
        text = args.registry.read_text(encoding="utf-8")
        baseline = yaml.safe_load(args.baseline.read_text(encoding="utf-8")) or []
        updates, left_alone = plan(audit, yaml.safe_load(text), baseline, today, args.only)
        new_text = apply(text, updates)
    except Refused as refusal:
        print(f"Refused. Nothing was written.\n  - {refusal}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, AttributeError, yaml.YAMLError) as error:
        print(f"Refused. Nothing was written.\n  - could not read the audit, sources, or baseline: {error!r}",
              file=sys.stderr)
        return 2

    if updates and not args.dry_run:
        args.registry.write_text(new_text, encoding="utf-8")
    report = summary(updates, left_alone, audit["audit_date"], args.dry_run)
    if args.dry_run:
        report = "Dry run: nothing was written.\n" + report
    print(report, end="")
    if args.summary:
        args.summary.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
