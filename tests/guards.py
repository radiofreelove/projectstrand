#!/usr/bin/env python3
"""Guards for the evidence audit's writes (Stage A of the upkeep automation design).

Every baseline write goes through the shared block below: the invariants
B1 to B6, the completeness diff, Ledgers 1 to 3, and the atomic writer.
A write that would leave the baseline worse is refused, with exit 3, and
nothing is written. The block is the same, line for line, in
tests/guards.py (The Strand Project) and tools/guards.py (The Stasis
Project); each project's tests check its hash. Below the block is this
project's adapter: the registry, baseline, and facts formats of The
Strand Project, the offline health vector, and the --reconcile and
--health commands.

    python3 tests/guards.py --reconcile   # Ledger 1 and the offline part of Ledger 3
    python3 tests/guards.py --health      # the offline health vector, as JSON
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# The baseline guards (begin)
#
# This block is the same, line for line, in tools/guards.py (The Stasis
# Project) and tests/guards.py (The Strand Project). Change it in both or
# in neither. Each project's tests check its hash (GUARDS_BLOCK_SHA256 in
# the guards tests). The block is pure: it works on entry dicts of the
# shape both audits use ({id, url, state, mode, sha256, rules,
# registry_checked, ...}) and never touches the filesystem except through
# atomic_write, which takes the path it is given.
#
# Exit codes, the same in both projects: 0 clean, 1 findings that need a
# person, 2 usage error, 3 unreconciled or a guard refused a write, 4 the
# run did not finish. Anything except 0 and 1 is a failed run.

EXIT_CLEAN, EXIT_FINDINGS, EXIT_USAGE, EXIT_REFUSED, EXIT_UNFINISHED = 0, 1, 2, 3, 4

STATE_BLOCKED = "checker-blocked"
STATE_UNREACHABLE = "unreachable"
RUN_CHANGED, RUN_UNCHANGED, RUN_NOT_BASELINED = "changed", "unchanged", "not yet baselined"


def _rank(entry: dict, current_rules: int) -> int:
    """An entry's strength, highest last: no hash, a hash under older
    rules, a hash under the current rules, the same with an attestation."""
    if not entry or not entry.get("sha256"):
        return 0
    if entry.get("rules") != current_rules:
        return 1
    return 3 if entry.get("attestation") else 2


def _hashed_current(entry: dict | None, url: str, current_rules: int) -> bool:
    return bool(entry and entry.get("sha256") and entry.get("url") == url
                and entry.get("rules") == current_rules)


def completeness_diff(old: dict, new: dict, retired: dict, current_rules: int,
                      label: str, today: str) -> list[str]:
    """What a baseline write would change, printed whether it is allowed
    or refused. old, new, and retired are {id: entry}; retired holds the
    entries the write moves to the baseline's retired list."""
    def hashed_current(entries):
        return {i for i, e in entries.items() if e.get("sha256") and e.get("rules") == current_rules}

    hc_old, hc_new = hashed_current(old), hashed_current(new)
    gained = sorted(i for i, e in new.items()
                    if e.get("sha256") and not (old.get(i) or {}).get("sha256"))
    lost = sorted(i for i, e in old.items()
                  if e.get("sha256") and not (new.get(i) or {}).get("sha256")
                  and not (retired.get(i) or {}).get("sha256"))
    changed = sorted(i for i, e in new.items()
                     if e.get("sha256") and (old.get(i) or {}).get("sha256")
                     and e["sha256"] != old[i]["sha256"])
    moves = sorted(f"{i} {old[i].get('state')} -> {new[i].get('state')}"
                   for i in new if i in old and old[i].get("state") != new[i].get("state"))
    att = sorted(f"{i} {'gained' if new[i].get('attestation') else 'lost'}"
                 for i in new if i in old
                 and bool(old[i].get("attestation")) != bool(new[i].get("attestation")))
    hc_delta = ""
    if hc_new != hc_old:
        delta = sorted(hc_new - hc_old) if len(hc_new) > len(hc_old) else sorted(hc_old - hc_new)
        hc_delta = f"   ({'+' if len(hc_new) > len(hc_old) else '-'}{abs(len(hc_new) - len(hc_old))}: {', '.join(delta)})"
    return [
        f"Baseline diff ({label}, {today}):",
        f"  entries: {len(old)} -> {len(new)}",
        f"  hashed under rules {current_rules}: {len(hc_old)} -> {len(hc_new)}{hc_delta}",
        f"  gained: {', '.join(gained) if gained else 'none'}",
        f"  lost: {', '.join(lost) if lost else 'none'}",
        f"  hash changed: {', '.join(changed) if changed else 'none'}",
        f"  state moves: {', '.join(moves) if moves else 'none'}",
        f"  attestation moves: {', '.join(att) if att else 'none'}",
    ]


def check_invariants(old: dict, new: dict, registry: dict, retired: dict,
                     old_written: str | None, new_written: str | None,
                     current_rules: int, accepted: dict, in_actions: bool) -> list[str]:
    """The baseline invariants B1 to B5 (B6 is the writer's round-trip).
    Returns the reasons a write must be refused; empty means it may go
    ahead. registry is {id: url}; accepted is {id: reason} from
    --accept-change; retired is {id: entry} the write sets aside."""
    reasons = []
    if in_actions and accepted:
        reasons.append("--accept-change is refused when GITHUB_ACTIONS is set: "
                       "a scheduled run can never accept a changed hash (B2)")
    for source_id in registry:
        if source_id not in new and source_id not in retired:
            reasons.append(f"{source_id}: missing from the new baseline (B4)")
    for source_id in new:
        if source_id not in registry:
            reasons.append(f"{source_id}: in the new baseline but not in the registry (B4)")
    for source_id, was in old.items():
        if not was.get("sha256"):
            continue
        now, gone = new.get(source_id), retired.get(source_id)
        if now and now.get("sha256") == was["sha256"] and now.get("url") == was.get("url"):
            continue
        if gone and gone.get("sha256") == was["sha256"] and gone.get("url") == was.get("url"):
            continue
        if now and now.get("sha256"):
            continue  # a different hash: B2 below decides
        reasons.append(f"{source_id}: its hash would be dropped (B1)")
    for source_id, now in new.items():
        was = old.get(source_id)
        if not was or not was.get("sha256") or not now.get("sha256"):
            continue
        if now["sha256"] == was["sha256"]:
            continue
        if (now.get("rules") or 1) > (was.get("rules") or 1):
            continue  # a re-hash of the same text under newer rules (carry-forward)
        if source_id in accepted and accepted[source_id] and not in_actions:
            continue
        reasons.append(f"{source_id}: its hash would change without --accept-change "
                       f"{source_id} --reason TEXT (B2)")
    for source_id, now in new.items():
        was = old.get(source_id)
        if not was:
            continue
        if was.get("sha256") and now.get("sha256") \
                and (now.get("rules") or 1) < (was.get("rules") or 1):
            reasons.append(f"{source_id}: its rules version would go down (B3)")
        if was.get("mode") and now.get("mode") and was["mode"] != now["mode"] \
                and source_id not in accepted:
            reasons.append(f"{source_id}: its comparison mode would change "
                           f"from {was['mode']} to {now['mode']} (B3)")
        if was.get("attestation") and not now.get("attestation"):
            reasons.append(f"{source_id}: its attestation would be removed (B3)")
        if was.get("earlier") and not now.get("earlier"):
            reasons.append(f"{source_id}: its 'earlier' result would be dropped (B3)")
        if was.get("registry_checked") and now.get("registry_checked") \
                and now["registry_checked"] < was["registry_checked"]:
            reasons.append(f"{source_id}: its registry_checked would move backward (B3)")
    # Coverage is measured over the registry as it now stands: a source a
    # person removed from the registry, retired with its hash, is not a
    # coverage loss.
    hc_old = sum(1 for i, e in old.items() if i in registry and _hashed_current(e, registry[i], current_rules))
    hc_new = sum(1 for i, e in new.items() if i in registry and _hashed_current(e, registry[i], current_rules))
    if hc_new < hc_old:
        reasons.append(f"coverage would fall: {hc_old} -> {hc_new} hashed under "
                       f"rules {current_rules} (B4)")
    if old_written and new_written and new_written < old_written:
        reasons.append(f"the baseline's written date would move backward: "
                       f"{old_written} -> {new_written} (B5)")
    return reasons


def ledger1(registry: dict, entries: dict, retired_ids: set, current_rules: int) -> tuple[str, list[str]]:
    """Ledger 1: registry against baseline, offline. Returns the equation
    line and the reasons it does not close. registry is {id: url};
    entries is {id: entry}."""
    hc = ho = blocked = unreachable = 0
    reasons = []
    for source_id, url in registry.items():
        entry = entries.get(source_id)
        if entry is None:
            reasons.append(f"{source_id}: in the registry but not in the baseline (Ledger 1)")
            continue
        if entry.get("sha256"):
            if entry.get("url") != url:
                reasons.append(f"{source_id}: the baseline's address does not match the registry (Ledger 1)")
            if entry.get("rules") == current_rules:
                hc += 1
            else:
                ho += 1
        elif entry.get("state") == STATE_BLOCKED:
            blocked += 1
        elif entry.get("state") == STATE_UNREACHABLE:
            unreachable += 1
        else:
            reasons.append(f"{source_id}: no hash and state {entry.get('state')!r}, "
                           f"which is neither blocked nor unreachable (Ledger 1)")
    for source_id in entries:
        if source_id not in registry and source_id not in retired_ids:
            reasons.append(f"{source_id}: in the baseline but not in the registry (Ledger 1)")
    line = f"{len(registry)} = {hc} + {ho} + {blocked} + {unreachable}"
    if hc + ho + blocked + unreachable != len(registry):
        reasons.append(f"the counts do not add up: {line} (Ledger 1)")
    return line, reasons


def ledger2(registry: dict, states: dict, baseline: dict, current_rules: int) -> list[str]:
    """Ledger 2: one run's results against the registry and the baseline.
    registry is {id: url} for the run's scope (the whole registry, or the
    --only list, which the caller labels partial); states is {id: state};
    baseline is {id: entry}. Every reason names its source."""
    reasons = []
    missing = sorted(set(registry) - set(states))
    if missing:
        reasons.append(f"no result for: {', '.join(missing)} (Ledger 2)")
    for source_id in sorted(set(states) - set(registry)):
        reasons.append(f"{source_id}: a result for a source outside the run's scope (Ledger 2)")
    compared = blocked_with_hash = hashed_in_scope = 0
    for source_id, state in states.items():
        if source_id not in registry:
            continue
        has = _hashed_current(baseline.get(source_id), registry[source_id], current_rules)
        if has:
            hashed_in_scope += 1
        if state in (RUN_CHANGED, RUN_UNCHANGED):
            compared += 1
            if not has:
                reasons.append(f"{source_id}: reported {state} but has no hash under "
                               f"rules {current_rules} (Ledger 2)")
        elif state == RUN_NOT_BASELINED:
            if has:
                reasons.append(f"{source_id}: reported not yet baselined but holds a hash "
                               f"under rules {current_rules} (Ledger 2)")
        elif state in (STATE_BLOCKED, STATE_UNREACHABLE) and has:
            blocked_with_hash += 1
    if compared + blocked_with_hash != hashed_in_scope:
        reasons.append(f"the compared and the hashed do not agree: {compared} compared + "
                       f"{blocked_with_hash} blocked or unreachable with a hash != "
                       f"{hashed_in_scope} hashed in scope (Ledger 2)")
    return reasons


def ledger3_cited(cited: set, registry_ids: set) -> list[str]:
    """The offline part of Ledger 3: every source a claim or fact cites
    is in the registry."""
    missing = sorted(cited - registry_ids)
    if missing:
        return [f"cited but not in the registry: {', '.join(missing)} (Ledger 3)"]
    return []


def atomic_write(path: Path, text: str, parse, expected, backup_dir: Path | None = None,
                 today: str | None = None, fail_after_temp: bool = False):
    """Write text to path atomically, or not at all (B6). The text is
    written to a temporary file in the same folder, read back, and parsed;
    the parsed entries must equal expected, or nothing is renamed over
    the old file. A copy of the file being replaced goes to backup_dir
    when one is given. fail_after_temp is a test hook: it raises after
    the temporary write, proving the old file survives a killed write."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp-guards")
    tmp.write_text(text, encoding="utf-8")
    try:
        if fail_after_temp:
            raise RuntimeError("injected failure after the temporary write (test)")
        if parse(tmp.read_text(encoding="utf-8")) != expected:
            raise ValueError("the written file does not read back as the entries "
                             "meant to be written (B6)")
        if backup_dir is not None and path.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = today or "undated"
            (backup_dir / f"{path.name}.{stamp}.bak").write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


# The baseline guards (end)
# ===========================================================================


# ---------------------------------------------------------------------------
# This project's adapter: The Strand Project's files

import datetime as dt
import re

import yaml

BASELINE = ROOT / "data" / "evidence_baseline.yml"
REGISTRY = ROOT / "data" / "sources.yml"
FACTS = ROOT / "data" / "facts.yml"

_WRITTEN = re.compile(r"^# written: (\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _rules() -> int:
    import evidence_audit
    return evidence_audit.RULES


def _iso(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    return value


def _norm(entries: list) -> list:
    """Entries as they read back from the YAML: dates as ISO strings,
    no None values (the dump drops them)."""
    return [{k: _iso(v) for k, v in e.items() if v is not None} for e in entries]


def load_registry(root: Path = ROOT) -> dict:
    data = yaml.safe_load((root / "data" / "sources.yml").read_text(encoding="utf-8")) or []
    return {src["id"]: src["url"] for src in data}


def load_baseline_file(path: Path = BASELINE) -> tuple[list, str | None, list]:
    """(active entries in file order, the written date, the retired
    entries). A retired entry stays in the file, marked with a retired
    date, so its hash is never simply lost (B1)."""
    if not path.exists():
        return [], None, []
    text = path.read_text(encoding="utf-8")
    match = _WRITTEN.search(text)
    entries = _norm(yaml.safe_load(text) or [])
    active = [e for e in entries if not e.get("retired")]
    retired = [e for e in entries if e.get("retired")]
    return active, (match.group(1) if match else None), retired


def parse_baseline_text(text: str) -> list:
    return _norm(yaml.safe_load(text) or [])


def citations(root: Path = ROOT) -> tuple[set, list]:
    """(every source id a fact cites, the facts' source lists)."""
    facts = yaml.safe_load((root / "data" / "facts.yml").read_text(encoding="utf-8")) or {}
    cited, lists = set(), []
    for fact in facts.values():
        sources = (fact or {}).get("sources", []) or []
        lists.append(sources)
        cited.update(sources)
    return cited, lists


def health_vector(root: Path = ROOT) -> dict:
    """The offline health vector: numbers from this repo's files alone,
    each of which should never fall. Test and check results are the
    checks workflow's own outcome, not recomputed here."""
    rules = _rules()
    registry = load_registry(root)
    entries, _, _ = load_baseline_file(root / "data" / "evidence_baseline.yml")
    by_id = {e["id"]: e for e in entries}
    _, source_lists = citations(root)
    return {
        "registry_sources": len(registry),
        "hashed_current_rules": sum(
            1 for i, e in by_id.items() if _hashed_current(e, registry.get(i, ""), rules)),
        "attested_entries": sum(1 for e in entries if e.get("attestation")),
        "facts_with_hashed_source": sum(
            1 for sources in source_lists
            if any(_hashed_current(by_id.get(s), registry.get(s, ""), rules) for s in sources)),
        "facts_total": len(source_lists),
    }


def reconcile(root: Path = ROOT) -> tuple[str, list[str]]:
    registry = load_registry(root)
    entries, _, retired = load_baseline_file(root / "data" / "evidence_baseline.yml")
    by_id = {e["id"]: e for e in entries}
    line, reasons = ledger1(registry, by_id, {e["id"] for e in retired}, _rules())
    cited, _ = citations(root)
    reasons += ledger3_cited(cited, set(registry))
    return line, reasons


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconcile", action="store_true",
                        help="check Ledger 1 and the offline part of Ledger 3, and print the equation")
    parser.add_argument("--health", action="store_true",
                        help="print the offline health vector as JSON")
    args = parser.parse_args(argv)
    if args.health:
        print(json.dumps(health_vector(), indent=2, sort_keys=True))
        return EXIT_CLEAN
    if args.reconcile:
        line, reasons = reconcile()
        print(line)
        for reason in reasons:
            print(f"Unreconciled: {reason}", file=sys.stderr)
        return EXIT_REFUSED if reasons else EXIT_CLEAN
    parser.print_usage(sys.stderr)
    return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
