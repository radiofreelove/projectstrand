#!/usr/bin/env python3
"""
Record what every source says, and report when that changes.

    python3 tests/evidence_audit.py --report FILE     Fetch every source, compare
                                                      it with the baseline, and
                                                      write a report to FILE
    python3 tests/evidence_audit.py --write-baseline  Fetch every source and
                                                      record what it says now
    python3 tests/evidence_audit.py --only ID ID      Only these sources (works
                                                      with both modes)

tests/check_external_links.py asks whether a source still answers. This
tool asks whether it still says the same thing. For every source in
data/sources.yml it:

  1. Reads the site's robots.txt and skips the address if robots.txt asks
     this tool to stay out.
  2. Asks for the address with GET, one request at a time, with a pause
     between requests, a time limit, and a user agent that names the
     project. If the reply is cut short, it waits and asks once more. A
     partial reply is never compared.
  3. Turns the reply into text that can be compared. For a web page: the
     words a reader sees, with tags, scripts, and styles removed and runs
     of spaces made into one. A PDF is not turned into text, because the
     project's declared test tools include no PDF library; its raw bytes
     are compared, and the baseline marks it "mode: bytes". A report that
     a "bytes" source changed is lower-confidence: a PDF saved again with
     the same words has new bytes.
  4. Compares the SHA-256 of that content with data/evidence_baseline.yml.

Every source ends in exactly one state:

  unchanged        The content matches the baseline.
  changed          It differs. For a web page the report shows what changed,
                   up to a limit. It names the facts in data/facts.yml that
                   cite the source and the pages that show those facts.
  unreachable      The connection failed, or the server answered with an
                   error other than 401 or 403.
  checker-blocked  The site answered 401 or 403 to this tool, or its
                   robots.txt keeps this tool out. This says nothing about
                   the source: it is not a dead link and not a removed
                   source. A person opens it.

A source the tool can read but that has no hash in the baseline is listed
as "not yet baselined". A missing hash is never counted as a change.

The baseline holds hashes, not text. To show what changed, the tool keeps
the text of each web page in a folder that is not committed (--snapshots,
by default .evidence-snapshots/). If the old text is not on hand, the
report says so and shows no diff.

The fact-to-page map comes from public/build-report.json, which build.py
writes: for each page, the facts it rendered. Run python3 build.py first.
Without it, the report still names the facts, and says the pages are not
known.

Exit code 1 if any source changed, otherwise 0. Blocked and unreachable
sources are reported and do not change the exit code; the link check is
what fails on an address that stopped answering. Exit code 2 on a usage
error. Needs PyYAML (requirements.txt); nothing else outside the standard
library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import http.client
import json
import re
import socket
import sys
import time
import unicodedata
import urllib.error
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REGISTRY = DATA / "sources.yml"
FACTS = DATA / "facts.yml"
BASELINE = DATA / "evidence_baseline.yml"
BUILD_REPORT = ROOT / "public" / "build-report.json"
SNAPSHOTS = ROOT / ".evidence-snapshots"

USER_AGENT = ("TheStrandProject-evidence-audit/0.1 (weekly source check; "
              "https://github.com/radiofreelove/projectstrand)")
TIMEOUT = 30          # seconds for one request
PAUSE = 1.5           # seconds between any two requests
HOST_PAUSE = 3.0      # seconds between two requests to the same site

UNCHANGED, CHANGED, UNREACHABLE, BLOCKED = "unchanged", "changed", "unreachable", "checker-blocked"
STATES = (UNCHANGED, CHANGED, UNREACHABLE, BLOCKED)
# Not a fifth verdict on the source: the tool read it, and has nothing to compare it with.
NOT_BASELINED = "not yet baselined"
FETCHED = "fetched"

# Stop reading a reply after this many bytes.
MAX_BYTES = 60_000_000
# Limits on what a report quotes, so the weekly issue stays readable and
# under GitHub's size limit for an issue body.
DIFF_LINES = 40
DIFF_LINE_CHARS = 240
DIFF_BUDGET = 24_000

BASELINE_HEADER = """\
# What each source in data/sources.yml returned to tests/evidence_audit.py.
# Written by: python3 tests/evidence_audit.py --write-baseline
# Do not edit by hand. See docs/OPERATIONS.md, "Evidence audit".
#
# These baselines rest on the project's November 2026 verified source
# checks (the "checked" dates in data/sources.yml, copied into
# registry_checked below). Writing a baseline is a tool fetching each
# address and storing a hash. It is not a fresh read of any source by a
# person.
#
#   url               the address fetched
#   fetched           the date of the fetch
#   state             fetched, checker-blocked, or unreachable
#   mode              text: the readable words of a web page
#                     bytes: the raw file (every PDF); a change report for
#                     a bytes source is lower-confidence
#   sha256, length    the hash and size of that content (characters for
#                     text, bytes for bytes). No sha256 means the source
#                     was blocked or unreachable and is not yet baselined.
#   registry_checked  the source's "checked" date when this entry was
#                     written: the verified check the hash rests on
#   note              why a source could not be read, when it could not
"""


# ---------------------------------------------------------------------------
# Turning content into text that can be compared

# Their content is not words on the page.
SKIPPED_TAGS = {"script", "style", "template", "svg", "noscript"}
# Tags that start a new line of text, so a diff shows one sentence or item per line.
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav",
    "ol", "option", "p", "pre", "section", "table", "td", "th", "title", "tr", "ul",
}


class ReadableText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIPPED_TAGS:
            self.skipping += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        # <br/> and the like: a line break, never a skipped block.
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in SKIPPED_TAGS:
            self.skipping = max(0, self.skipping - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skipping:
            # A line break in the page's source is only a space to a reader.
            lead = " " if data[:1].isspace() else ""
            trail = " " if data[-1:].isspace() else ""
            self.parts.append(lead + " ".join(data.split()) + trail)


def collapse(text: str) -> str:
    """One line per block of text, single spaces, no empty lines."""
    text = unicodedata.normalize("NFC", text)
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def html_text(markup: str) -> str:
    """The words a reader sees on a web page: one line for each heading,
    paragraph, list item, or table cell."""
    parser = ReadableText()
    parser.feed(markup)
    parser.close()
    return collapse("".join(parser.parts))


def is_pdf(body: bytes, content_type: str) -> bool:
    return body.lstrip()[:5] == b"%PDF-" or "application/pdf" in content_type


def charset_of(content_type: str) -> str:
    found = re.search(r"charset=\"?([\w.-]+)", content_type, re.I)
    return found.group(1) if found else "utf-8"


def normalize(body: bytes, content_type: str = ""):
    """Return (mode, text or None, sha256, length) for a reply.

    "text" mode hashes the readable text, and "length" counts its
    characters. "bytes" mode hashes the reply as it came, and "length"
    counts its bytes.
    """
    content_type = content_type.lower()
    if is_pdf(body, content_type):
        return "bytes", None, hashlib.sha256(body).hexdigest(), len(body)
    try:
        decoded = body.decode(charset_of(content_type), "replace")
    except LookupError:  # a charset Python does not know
        decoded = body.decode("utf-8", "replace")
    if "html" in content_type or re.search(r"<(!doctype|html|head|body)\b", decoded[:4000], re.I):
        text = html_text(decoded)
    elif content_type.startswith("text/") or not content_type:
        text = collapse(decoded)
    else:
        return "bytes", None, hashlib.sha256(body).hexdigest(), len(body)
    return "text", text, hashlib.sha256(text.encode("utf-8")).hexdigest(), len(text)


# ---------------------------------------------------------------------------
# Fetching, politely

def load_sources(path: Path | None = None) -> list:
    return yaml.safe_load((path or REGISTRY).read_text(encoding="utf-8"))


class Robots:
    """robots.txt for each site, read once per run with this tool's user agent."""

    def __init__(self, opener=None):
        self.open = opener or (lambda req: urllib.request.urlopen(req, timeout=TIMEOUT))
        self.cache: dict[str, tuple] = {}

    def check(self, url: str):
        """(allowed, note). note says why not, when not."""
        parts = urlsplit(url)
        site = f"{parts.scheme}://{parts.netloc}"
        if site not in self.cache:
            self.cache[site] = self._read(site)
        parser, refusal = self.cache[site]
        if refusal:
            return False, refusal
        if parser is None or parser.can_fetch(USER_AGENT, url):
            return True, None
        return False, "robots.txt asks automated visitors not to load this address"

    def _read(self, site: str):
        request = urllib.request.Request(site + "/robots.txt", headers={"User-Agent": USER_AGENT})
        try:
            with self.open(request) as response:
                text = response.read(500_000).decode("utf-8", "replace")
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                # The robots.txt convention: a refused robots.txt means "stay out".
                return None, f"the site answered {error.code} to this tool's request for robots.txt"
            return None, None  # no robots.txt: no rules
        except Exception:
            return None, None  # the fetch itself will say whether the site answers
        parser = urllib.robotparser.RobotFileParser()
        parser.parse(text.splitlines())
        return parser, None


# A reply that stops partway is never compared: it is not what the source says.
CUT_SHORT = (http.client.IncompleteRead, http.client.RemoteDisconnected, ConnectionResetError)


def fetch(url: str, opener=None) -> dict:
    """Ask for one address. Returns "state" (fetched, unreachable, or
    checker-blocked) and, when fetched, the content."""
    opener = opener or (lambda req: urllib.request.urlopen(req, timeout=TIMEOUT))
    asked_again = False
    while True:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with opener(request) as response:
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    return {"state": UNREACHABLE, "note": f"the reply is larger than {MAX_BYTES} bytes; not compared"}
                mode, text, digest, length = normalize(body, response.headers.get("Content-Type", "") or "")
                return {"state": FETCHED, "mode": mode, "text": text, "sha256": digest, "length": length}
        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                return {"state": BLOCKED, "note": f"the site answered {error.code} to this tool"}
            return {"state": UNREACHABLE, "note": f"HTTP {error.code}"}
        except Exception as error:  # network failure, timeout, TLS, cut short
            reason = getattr(error, "reason", error)
            if isinstance(reason, CUT_SHORT) or isinstance(error, CUT_SHORT):
                if not asked_again:
                    asked_again = True
                    time.sleep(PAUSE)
                    continue
            if isinstance(reason, (socket.timeout, TimeoutError)):
                note = "timed out"
            else:
                note = f"{reason.__class__.__name__}: {reason}" if isinstance(reason, BaseException) else str(reason)
            return {"state": UNREACHABLE, "note": note + ("; asked twice" if asked_again else "")}


def fetch_all(entries, fetcher=fetch, robots=None, pause: float = PAUSE, host_pause: float = HOST_PAUSE,
              sleep=time.sleep):
    """Fetch each source in order, one at a time. Yields (source, result)."""
    robots = robots or Robots()
    last_any = 0.0
    last_host: dict[str, float] = {}
    for src in entries:
        url = src["url"]
        host = urlsplit(url).netloc
        wait = max(pause - (time.time() - last_any), host_pause - (time.time() - last_host.get(host, 0.0)))
        if last_any and wait > 0:
            sleep(wait)
        allowed, note = robots.check(url)
        if not allowed:
            yield src, {"state": BLOCKED, "note": note}
            continue
        result = fetcher(url)
        last_any = last_host[host] = time.time()
        yield src, result


# ---------------------------------------------------------------------------
# The baseline

def as_iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()[:10]
    return str(value)


def load_baseline(path: Path) -> dict:
    """The baseline as {source id: entry}. A missing or empty file is an empty baseline."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    out = {}
    for entry in data:
        entry = dict(entry)
        for key in ("fetched", "registry_checked"):
            if key in entry:
                entry[key] = as_iso(entry[key])
        out[entry["id"]] = entry
    return out


def baseline_entry(src: dict, result: dict, today: str) -> dict:
    entry = {
        "id": src["id"],
        "url": src["url"],
        "fetched": today,
        "state": result["state"],
        "mode": result.get("mode"),
        "sha256": result.get("sha256"),
        "length": result.get("length"),
        "registry_checked": as_iso(src.get("checked")),
    }
    if result.get("note"):
        entry["note"] = result["note"]
    return entry


def merge_baseline(old: dict, fresh: dict, order: list) -> tuple[list, list]:
    """Put freshly fetched entries into a baseline. Returns (entries, kept).

    A refresh never throws away a hash it cannot replace: if a source was
    blocked or unreachable this time and the old entry holds a hash for
    the same address, the old entry stays. "kept" lists those ids.
    Sources that left the registry are dropped.
    """
    entries, kept = [], []
    for source_id in order:
        new, was = fresh.get(source_id), old.get(source_id)
        if new is None:
            if was:
                entries.append(was)
            continue
        if new["sha256"] is None and was and was.get("sha256") and was.get("url") == new["url"]:
            entries.append(was)
            kept.append(source_id)
        else:
            entries.append(new)
    return entries, kept


def dump_baseline(entries: list) -> str:
    """The baseline file's text: the header, then one block per source."""
    blocks = []
    for entry in entries:
        clean = {k: v for k, v in entry.items() if v is not None}
        for key in ("fetched", "registry_checked"):
            if key in clean:
                clean[key] = dt.date.fromisoformat(clean[key])
        blocks.append(yaml.safe_dump([clean], sort_keys=False, allow_unicode=True, width=1000))
    return BASELINE_HEADER + "\n" + "\n".join(blocks)


def save_baseline(path: Path, entries: list):
    path.write_text(dump_baseline(entries), encoding="utf-8")


def snapshot_path(folder: Path, source_id: str) -> Path:
    return folder / (re.sub(r"[^A-Za-z0-9._-]", "_", source_id) + ".txt")


def save_snapshot(folder: Path, source_id: str, text: str | None):
    if text is None:
        return
    folder.mkdir(parents=True, exist_ok=True)
    snapshot_path(folder, source_id).write_text(text, encoding="utf-8")


def load_snapshot(folder: Path, source_id: str, digest: str) -> str | None:
    """The saved text for a source, only if it is the text the baseline hashed."""
    path = snapshot_path(folder, source_id)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return text if hashlib.sha256(text.encode("utf-8")).hexdigest() == digest else None


# ---------------------------------------------------------------------------
# Comparing

def has_baseline(entry: dict | None, url: str) -> bool:
    return bool(entry and entry.get("sha256") and entry.get("url") == url)


def classify(result: dict, entry: dict | None, url: str) -> str:
    """One state for one source, from this run's fetch and its baseline entry."""
    if result["state"] != FETCHED:
        return result["state"]
    if not has_baseline(entry, url):
        return NOT_BASELINED
    return UNCHANGED if result["sha256"] == entry["sha256"] else CHANGED


def bounded_diff(old: str, new: str, limit: int = DIFF_LINES, width: int = DIFF_LINE_CHARS) -> str:
    """A unified diff of two normalized texts, cut to a fixed size."""
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "baseline", "now", lineterm="", n=1))
    shown = [line if len(line) <= width else line[:width] + " [cut]" for line in lines[:limit]]
    if len(lines) > limit:
        shown.append(f"[{len(lines) - limit} more diff lines not shown]")
    # Three backticks in a source would end the report's code block early.
    return "\n".join(shown).replace("```", "'''")


# ---------------------------------------------------------------------------
# Which facts and pages rest on a source

def load_build_report(path: Path = BUILD_REPORT) -> dict | None:
    """public/build-report.json, if the build has written one that lists facts per page."""
    if not path.exists():
        return None
    report = json.loads(path.read_text(encoding="utf-8"))
    if not all("facts" in page for page in report.get("pages", [])):
        return None  # built before build.py recorded facts per page
    return report


def fact_pages(build_report: dict | None) -> dict | None:
    """{fact id: [page slugs that render it]}, from what the build rendered."""
    if build_report is None:
        return None
    usage: dict[str, list] = {}
    for page in build_report["pages"]:
        for fid in page.get("facts", []):
            usage.setdefault(fid, []).append(page["slug"])
    return usage


def source_pages(build_report: dict | None) -> dict | None:
    """{source id: [page slugs that cite it]}, from what the build rendered."""
    if build_report is None:
        return None
    cited: dict[str, list] = {}
    for page in build_report["pages"]:
        for sid in page.get("sources", []):
            cited.setdefault(sid, []).append(page["slug"])
    return cited


def exposure(source_id: str, facts: dict, usage: dict | None) -> list:
    """[(fact id, [pages] or None)] for the facts that cite a source.
    Pages are None when the build report is not on hand."""
    return [(fid, None if usage is None else sorted(usage.get(fid, [])))
            for fid, fact in facts.items() if source_id in (fact or {}).get("sources", [])]


# ---------------------------------------------------------------------------
# The report

def render_report(rows: list, baseline: dict, registry_ids: set, facts: dict, build_report: dict | None,
                  snapshots: Path, today: str, partial: bool = False) -> str:
    """rows: (source, result, state) for each source audited."""
    usage, cited_by = fact_pages(build_report), source_pages(build_report)

    def of(state):
        return [(src, result) for src, result, found in rows if found == state]

    def was(src):
        entry = baseline.get(src["id"])
        if has_baseline(entry, src["url"]):
            return f"It was readable when its baseline was set on {entry['fetched']}."
        return "It has no baseline yet."

    changed, unreachable, blocked = of(CHANGED), of(UNREACHABLE), of(BLOCKED)
    fresh, same = of(NOT_BASELINED), of(UNCHANGED)
    no_hash = [(src, found) for src, result, found in rows
               if found in (UNREACHABLE, BLOCKED) and not has_baseline(baseline.get(src["id"]), src["url"])]

    lines = [
        "# Evidence audit report", "",
        f"Run on {today}. Compared {len(rows)} sources with data/evidence_baseline.yml."
        + (" Only the sources named with --only were audited." if partial else ""), "",
        "| State | Sources |", "|---|---|",
        f"| Changed | {len(changed)} |", f"| Unchanged | {len(same)} |",
        f"| Unreachable | {len(unreachable)} |", f"| Checker-blocked | {len(blocked)} |",
        f"| Not yet baselined (readable now) | {len(fresh)} |", "",
        "A change is a prompt for a person to re-read the source. It does not say a fact on the site is wrong. "
        "Checker-blocked means this tool was refused; it never means the link is dead. "
        "See docs/OPERATIONS.md, \"Evidence audit\".", "",
        f"## Changed ({len(changed)})", "",
    ]
    if changed and usage is None:
        lines += ["public/build-report.json was not on hand (or was built before it listed facts per page), "
                  "so the pages below are not known. Run `python3 build.py`, then this audit again.", ""]
    budget = DIFF_BUDGET
    for src, result in changed:
        entry = baseline[src["id"]]
        lines += [f"### {src['id']}: {src.get('short') or src['title']}", "", f"- Address: {src['url']}",
                  f"- Baseline set on {entry['fetched']}, resting on the source check of "
                  f"{entry.get('registry_checked') or 'an unrecorded date'}."]
        cited = exposure(src["id"], facts, usage)
        if cited:
            lines.append("- Facts in data/facts.yml that cite it, and the pages that show them:")
            for fid, pages in cited:
                where = "pages not known (no build report)" if pages is None else (", ".join(pages) or "no page")
                lines.append(f"  - {fid}: {where}")
        else:
            lines.append("- No fact in data/facts.yml cites it.")
        if cited_by is not None:
            shown = {page for _, pages in cited for page in (pages or [])}
            also = sorted(set(cited_by.get(src["id"], [])) - shown)
            if also:
                lines.append(f"- Pages that cite it directly, not through a fact: {', '.join(also)}")
        old = load_snapshot(snapshots, src["id"], entry["sha256"]) if entry.get("mode") == "text" else None
        if result["mode"] != "text" or entry.get("mode") != "text":
            lines += ["", f"Compared as {entry.get('mode')} then, {result['mode']} now. A file compared by its bytes "
                          "has no text to show. Lower confidence: the same words saved again have new bytes. "
                          f"Size then: {entry.get('length')}. Size now: {result['length']}. Open it and compare."]
        elif old is None:
            lines += ["", "The baseline text is not on hand on this computer, so there is no diff to show. "
                          f"Length then: {entry.get('length')} characters. Length now: {result['length']}."]
        else:
            diff = bounded_diff(old, result["text"])
            if len(diff) > budget:
                lines += ["", "The diff is left out to keep this report short. Run "
                              f"`python3 tests/evidence_audit.py --only {src['id']} --report FILE` to see it."]
            else:
                budget -= len(diff)
                lines += ["", "What changed in the page's text (cut to a limit):", "", "```diff", diff, "```"]
        lines.append("")

    lines += [f"## Unreachable ({len(unreachable)})", "",
              "The connection failed or the server answered with an error. Not compared this time.", ""]
    lines += [f"- {src['id']}: {src['url']} ({result['note']}). {was(src)}" for src, result in unreachable] + [""]
    lines += [f"## Checker-blocked ({len(blocked)})", "",
              "These sites do not let this tool read them. That says nothing about the source: it is not a dead "
              "link and not a removed source. A person opens these by hand.", ""]
    lines += [f"- {src['id']}: {src['url']} ({result['note']}). {was(src)}" for src, result in blocked] + [""]
    lines += [f"## Not yet baselined ({len(fresh) + len(no_hash)})", "",
              "No stored hash to compare with. This is not a change. After a person has read the source, run "
              "`python3 tests/evidence_audit.py --write-baseline --only ID`.", ""]
    for src, _ in fresh:
        moved = baseline.get(src["id"], {}).get("url") not in (None, src["url"])
        why = "its address changed since the baseline" if moved else "no stored hash"
        lines.append(f"- {src['id']}: {src['url']} (readable now; {why})")
    lines += [f"- {src['id']}: {src['url']} ({found} now)" for src, found in no_hash]
    lines.append("")
    gone = sorted(set(baseline) - registry_ids)
    if gone:
        lines += ["## In the baseline but not in data/sources.yml", "",
                  ", ".join(gone) + ". The next deliberate baseline refresh drops them.", ""]
    lines += [f"## Unchanged ({len(same)})", "", ", ".join(src["id"] for src, _ in same) or "None.", ""]
    return "\n".join(lines)


def results_data(rows: list, today: str) -> dict:
    """The run in a form tests/mechanical_update.py reads."""
    return {
        "audit_date": today,
        "results": [
            {"id": src["id"], "url": src["url"], "state": state, "mode": result.get("mode"),
             "sha256": result.get("sha256"), "length": result.get("length"), "note": result.get("note")}
            for src, result, state in rows
        ],
    }


def main(argv=None, fetcher=fetch, robots=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path, help="write the Markdown report to this file")
    parser.add_argument("--write-baseline", action="store_true",
                        help="record what each source says now, instead of comparing")
    parser.add_argument("--only", nargs="+", metavar="ID", help="only these source ids")
    parser.add_argument("--results", type=Path, help="also write the run as JSON, for tests/mechanical_update.py")
    parser.add_argument("--baseline", type=Path, default=BASELINE, help="the baseline file (for tests)")
    parser.add_argument("--registry", type=Path, default=REGISTRY, help="a sources file (for tests)")
    parser.add_argument("--facts", type=Path, default=FACTS, help="a facts file (for tests)")
    parser.add_argument("--build-report", type=Path, default=BUILD_REPORT, help="a build report (for tests)")
    parser.add_argument("--snapshots", type=Path, default=SNAPSHOTS,
                        help="folder for the text of each web page, used to show what changed; not committed")
    parser.add_argument("--today", help="YYYY-MM-DD, for testing")
    args = parser.parse_args(argv)
    today = args.today or dt.date.today().isoformat()

    registry = load_sources(args.registry)
    entries = registry
    if args.only:
        unknown = sorted(set(args.only) - {src["id"] for src in registry})
        if unknown:
            print(f"Not in data/sources.yml: {', '.join(unknown)}", file=sys.stderr)
            return 2
        entries = [src for src in registry if src["id"] in args.only]
    baseline = load_baseline(args.baseline)

    if args.write_baseline:
        fresh, counts = {}, {}
        for src, result in fetch_all(entries, fetcher=fetcher, robots=robots):
            fresh[src["id"]] = baseline_entry(src, result, today)
            counts[result["state"]] = counts.get(result["state"], 0) + 1
            if result["state"] == FETCHED:
                save_snapshot(args.snapshots, src["id"], result["text"])
            print(f"{src['id']}: {result['state']}" + (f" ({result['note']})" if result.get("note") else ""),
                  flush=True)
        merged, kept = merge_baseline(baseline, fresh, [src["id"] for src in registry])
        save_baseline(args.baseline, merged)
        print(f"\nWrote {args.baseline} ({len(merged)} entries; {len(fresh)} fetched in this run).")
        for state in (FETCHED, BLOCKED, UNREACHABLE):
            print(f"  {state}: {counts.get(state, 0)}")
        modes = [entry["mode"] for entry in fresh.values() if entry["mode"]]
        print(f"  compared as text: {modes.count('text')}; as bytes: {modes.count('bytes')}")
        if kept:
            print("  Kept the earlier hash for sources that could not be read this time: " + ", ".join(kept))
        return 0

    rows = []
    for src, result in fetch_all(entries, fetcher=fetcher, robots=robots):
        entry = baseline.get(src["id"])
        state = classify(result, entry, src["url"])
        if state == UNCHANGED and result["mode"] == "text" and \
                load_snapshot(args.snapshots, src["id"], entry["sha256"]) is None:
            # The text matches the baseline's hash, so it is the baseline text. Keep it for a later diff.
            save_snapshot(args.snapshots, src["id"], result["text"])
        rows.append((src, result, state))

    facts = yaml.safe_load(args.facts.read_text(encoding="utf-8")) or {}
    report = render_report(rows, baseline, {src["id"] for src in registry}, facts,
                           load_build_report(args.build_report), args.snapshots, today, partial=bool(args.only))
    print(report)
    if args.report:
        args.report.write_text(report, encoding="utf-8")
    if args.results:
        args.results.write_text(json.dumps(results_data(rows, today), indent=2) + "\n", encoding="utf-8")
    return 1 if any(state == CHANGED for _, _, state in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
