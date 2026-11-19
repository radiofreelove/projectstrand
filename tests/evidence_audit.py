#!/usr/bin/env python3
"""
Record what every source says, and report when that changes.

    python3 tests/evidence_audit.py --report FILE     Fetch every source, compare
                                                      it with the baseline, and
                                                      write a report to FILE
    python3 tests/evidence_audit.py --write-baseline  Fetch every source and
                                                      record what it says now
    python3 tests/evidence_audit.py --carry-forward   Re-hash entries written
                                                      under older comparison
                                                      rules from their saved
                                                      text; fetches nothing
    python3 tests/evidence_audit.py --only ID ID      Only these sources (works
                                                      with every mode)

tests/check_external_links.py asks whether a source still answers. This
tool asks whether it still says the same thing. For every source in
data/sources.yml it:

  1. Reads the site's robots.txt and skips the address if robots.txt asks
     this tool to stay out.
  2. Asks for the address with GET, one request at a time, with a pause
     between requests, a time limit, and a user agent that names the
     project. If the reply is cut short (the connection fails partway, or
     fewer bytes arrive than the reply announced), it waits and asks once
     more. A partial reply is never compared.
  3. Turns the reply into text that can be compared. For a web page: the
     words a reader sees, with tags, scripts, and styles removed. The hash
     is taken over the words alone, so where the lines break does not
     count. A reply that is a check for automated visitors, or that has no
     readable words or too few to be a source, is not the source and is
     never hashed. A PDF is not turned into text, because the project's
     declared test tools include no PDF library; its raw bytes are
     compared, and the baseline marks it "mode: bytes". A report that a
     "bytes" source changed is lower-confidence: a PDF saved again with the
     same words has new bytes. A few pages carry a line that changes on
     every load (a server name, a random form label); the VOLATILE list
     below names each one, and that line is dropped before hashing.
  4. Compares the SHA-256 of that content with data/evidence_baseline.yml.

These are "the comparison rules", in the block of that name below. They
are the same in The Stasis Project's audit, and RULES numbers them.

Every source ends in exactly one state:

  unchanged        The content matches the baseline.
  changed          It differs. For a web page the report shows what changed,
                   up to a limit. It names the facts in data/facts.yml that
                   cite the source and the pages that show those facts.
  unreachable      The connection failed, or the server answered with an
                   error other than 401 or 403.
  checker-blocked  The site answered 401 or 403 to this tool, its
                   robots.txt keeps this tool out, or it answered with a
                   check for automated visitors (or a page with no words,
                   or too few) instead of the source. This says nothing about
                   the source: it is not a dead link and not a removed
                   source. A person opens it.

A source the tool can read but that has no hash in the baseline is listed
as "not yet baselined". So is one whose hash was written under other
comparison rules. A missing hash is never counted as a change.

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
import os
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

import guards  # Stage A: every baseline write goes through the guard

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
#   rules             the version of the comparison rules the hash was
#                     taken under (RULES in the tool); an entry under other
#                     rules is not compared
#   carried           the hash was re-taken from the saved text of the
#                     earlier fetch, without fetching again
#   earlier           whether this fetch said the same as the hash it
#                     replaced; if different, a person reads the source
#                     before this hash is relied on
#   note              why a source could not be read, or which lines that
#                     change on every load were dropped before hashing
"""


# ===========================================================================
# The comparison rules (begin)
#
# This block is the same, line for line, in tools/evidence_audit.py (The
# Stasis Project) and tests/evidence_audit.py (The Strand Project). Change
# it in both or in neither, so the two audits keep one set of rules. Each
# project's tests check its hash (RULES_BLOCK_SHA256 in the audit's tests).
#
# The rules exist so that a baseline written on one computer can be
# compared with a fetch made on another. In November 2026 three things
# made unchanged pages look changed:
#
#   1. Where the lines break. One copy of the tool turned each line break
#      in a page's source into a new line of text; another made it a
#      space. Neither changes a word a reader sees. So the hash is taken
#      over the words alone, in order, with every run of spaces, line
#      breaks, and invisible characters made into one space; and the diff
#      compares words, so a line that was only joined or split is never
#      shown as a change.
#   2. How much of the reply arrived. Some servers close the connection
#      partway through a reply. When the tool reads a reply up to a size
#      limit, Python returns the part that arrived and raises no error, so
#      part of a page or part of a PDF was hashed as if it were the whole.
#      Now a reply shorter than its Content-Length is cut short, and so is
#      a PDF sent without a Content-Length that has no end-of-file marker.
#      A cut-short reply is asked for once more and never hashed. A reply
#      with no Content-Length that is not a PDF cannot be checked this way;
#      a chunked reply that stops partway still raises an error, but a reply
#      that simply ends early does not. That gap is known, and is why a
#      change report is a prompt for a person, never a verdict.
#   3. Pages that are not the source. Some sites answer automated visitors
#      with a page that checks for them ("Please wait while your request is
#      being verified", a CAPTCHA), or with a page that has no readable
#      words and sends the browser elsewhere. Which one a fetch gets can
#      vary from one fetch to the next. Such a reply is never hashed: it is
#      checker-blocked, and a person opens the source. A check page that
#      is hashed is the worst case: the next fetch gets the same check page,
#      and the source is called unchanged although its words were never
#      read. So a reply with fewer than MIN_WORDS words is not taken as the
#      source either, whatever it says: every source of these projects has
#      well over a hundred words, and every check page seen has a dozen.
#
# RULES numbers these rules. Every baseline entry records the RULES it was
# written under. An entry written under other rules is never compared,
# because its hash means something else: it is listed as not yet
# baselined until it is written again (--write-baseline) or carried
# forward from its saved text (--carry-forward). Raise RULES whenever a
# change in this block would change a hash. (A rule that only refuses more
# replies, like MIN_WORDS, changes no hash.)
#
# Three more rules keep a baseline honest when it is written again:
#
#   - A refresh never throws away a hash it cannot replace, even one
#     written under older rules: that hash cannot be compared, but it can
#     still be carried forward, or checked against the next whole fetch.
#   - Carrying forward re-takes a text hash from the saved text. A file
#     compared by its bytes has no saved copy, and under older rules a reply
#     cut short was hashed as if whole (in November 2026, 9 of 37 PDF
#     hashes), so a bytes hash is never carried forward. It is written
#     again from a whole fetch.
#   - When a fresh fetch replaces a hash, the new entry says whether it
#     says what the old hash said ("earlier"). The same words or bytes
#     carry the old entry's verified check forward. Different ones mean the
#     source changed, or the old hash was not of the whole source; either
#     way a person reads the source before the new hash is relied on.
RULES = 2

# Their content is not words on the page a reader sees.
SKIPPED_TAGS = {"script", "style", "template", "svg", "noscript"}
# Tags that start a new line of text, so a diff shows one sentence or item per line.
BLOCK_TAGS = {
    "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "fieldset", "figcaption",
    "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "hr", "li", "main", "nav",
    "ol", "option", "p", "pre", "section", "table", "td", "th", "title", "tr", "ul",
}
# Characters a reader never sees: zero-width space, word joiner, byte-order mark, soft hyphen.
INVISIBLE = dict.fromkeys(map(ord, "​⁠﻿­"))


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
    text = unicodedata.normalize("NFC", text).translate(INVISIBLE)
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def html_text(markup: str) -> str:
    """The words a reader sees on a web page: one line for each heading,
    paragraph, list item, or table cell. The lines are for people reading
    a diff; the hash does not depend on them (see canonical)."""
    parser = ReadableText()
    parser.feed(markup)
    parser.close()
    return collapse("".join(parser.parts))


def canonical(text: str) -> str:
    """What is hashed: the words in order, separated by single spaces.
    Where the lines break is not part of it."""
    return " ".join(unicodedata.normalize("NFC", text).translate(INVISIBLE).split())


def text_digest(text: str, rules: int = RULES) -> str:
    """The hash of a page's text under a given set of rules. Rules 1, used
    until November 2026, hashed the text exactly as it was saved."""
    return hashlib.sha256((text if rules == 1 else canonical(text)).encode("utf-8")).hexdigest()


def drop_volatile(text: str, source_id: str) -> str:
    """The text without the lines VOLATILE names for this source."""
    rules = VOLATILE.get(source_id)
    if not rules or text is None:
        return text
    lines = text.split("\n")
    patterns = [re.compile(p) for p in rules.get("lines", [])]
    drop = {i for i, line in enumerate(lines) if any(p.fullmatch(line) for p in patterns)}
    for marker in rules.get("before", []):
        drop |= {i - 1 for i, line in enumerate(lines) if line == marker and i > 0}
    return "\n".join(line for i, line in enumerate(lines) if i not in drop)


def apply_volatile(result: dict, source_id: str) -> dict:
    """Re-hash a fetched page's text without its volatile lines."""
    if result.get("state") != FETCHED or result.get("mode") != "text" or source_id not in VOLATILE:
        return result
    text = drop_volatile(result["text"], source_id)
    return {**result, "text": text, "sha256": text_digest(text), "length": len(canonical(text)),
            "note": "drops lines that change on every load: " + VOLATILE[source_id]["why"]}


def is_pdf(body: bytes, content_type: str) -> bool:
    return body.lstrip()[:5] == b"%PDF-" or "application/pdf" in content_type


def is_html(decoded: str, content_type: str) -> bool:
    return "html" in content_type or bool(re.search(r"<(!doctype|html|head|body)\b", decoded[:4000], re.I))


def charset_of(content_type: str) -> str:
    found = re.search(r"charset=\"?([\w.-]+)", content_type, re.I)
    return found.group(1) if found else "utf-8"


def decode(body: bytes, content_type: str) -> str:
    try:
        return body.decode(charset_of(content_type), "replace")
    except LookupError:  # a charset Python does not know
        return body.decode("utf-8", "replace")


def normalize(body: bytes, content_type: str = ""):
    """Return (mode, text or None, sha256, length) for a reply.

    "text" mode hashes the canonical form of the readable text, and
    "length" counts its characters. "bytes" mode hashes the reply as it
    came, and "length" counts its bytes.
    """
    content_type = content_type.lower()
    if is_pdf(body, content_type):
        return "bytes", None, hashlib.sha256(body).hexdigest(), len(body)
    decoded = decode(body, content_type)
    if is_html(decoded, content_type):
        text = html_text(decoded)
    elif content_type.startswith("text/") or not content_type:
        text = collapse(decoded)
    else:
        return "bytes", None, hashlib.sha256(body).hexdigest(), len(body)
    return "text", text, text_digest(text), len(canonical(text))


class CutShort(Exception):
    """A reply that arrived without an error but is not whole."""


def check_whole(body: bytes, content_type: str, declared: str | None):
    """Raise CutShort if a reply is not all there. declared is the reply's
    Content-Length header, if it had one. With one, it decides. Without
    one, a PDF must end with its end-of-file marker."""
    if declared and declared.strip().isdigit():
        if len(body) < int(declared):
            raise CutShort(f"the reply stopped at {len(body)} of the {int(declared)} bytes it announced")
        return
    if is_pdf(body, (content_type or "").lower()) and b"%%EOF" not in body[-2048:]:
        raise CutShort(f"the PDF stops at {len(body)} bytes with no end-of-file marker")


# A page that checks for automated visitors instead of showing the source.
# The first two were seen on sources of these projects in November 2026;
# the others are the wording of common checks. Only short pages are
# tested, so a long page that quotes one of these phrases is still read.
CHALLENGE_PHRASES = (
    "please wait while your request is being verified",
    "your request has been flagged as potentially automated",
    "checking your browser before accessing",
    "checking if the site connection is secure",
    "needs to review the security of your connection",
    "enable javascript and cookies to continue",
    "verify you are human",
    "verifying you are human",
    "incapsula incident id",
    "pardon our interruption",
)
CHALLENGE_MAX_CHARS = 3000
# Fewer words than this, and a reply is not taken as the source (see 3 above).
# The shortest source text in either project in November 2026 had 165 words.
MIN_WORDS = 50


def not_the_source(mode: str, text: str | None) -> str | None:
    """Why a readable reply is not the source, or None if it may be."""
    if mode != "text":
        return None
    words = canonical(text or "")
    if not words:
        return "the reply has no readable words (the site may have sent a check for automated visitors)"
    if len(words) <= CHALLENGE_MAX_CHARS:
        lowered = words.lower()
        for phrase in CHALLENGE_PHRASES:
            if phrase in lowered:
                return f'the site answered with a check for automated visitors ("{phrase}"), not the source'
    count = len(words.split())
    if count < MIN_WORDS:
        return (f"the reply has only {count} words, too few to be the source "
                "(the site may have sent a check for automated visitors, or an error page)")
    return None


def examine(body: bytes, content_type: str, declared: str | None) -> dict:
    """Turn a whole reply into a result: fetched, or checker-blocked if it
    is not the source. Raises CutShort if the reply is not whole."""
    check_whole(body, content_type, declared)
    mode, text, digest, length = normalize(body, content_type)
    why = not_the_source(mode, text)
    if why:
        return {"state": BLOCKED, "note": why}
    return {"state": FETCHED, "mode": mode, "text": text, "sha256": digest, "length": length}


def has_baseline(entry: dict | None, url: str) -> bool:
    """True if an entry holds a hash this run can compare with."""
    return bool(entry and entry.get("sha256") and entry.get("url") == url and entry.get("rules") == RULES)


def older_rules(entry: dict | None, url: str) -> bool:
    """True if an entry holds a hash for this address, written under other rules."""
    return bool(entry and entry.get("sha256") and entry.get("url") == url and entry.get("rules") != RULES)


def classify(result: dict, entry: dict | None, url: str) -> str:
    """One state for one source, from this run's fetch and its baseline entry."""
    if result["state"] != FETCHED:
        return result["state"]
    if not has_baseline(entry, url):
        return NOT_BASELINED
    return UNCHANGED if result["sha256"] == entry["sha256"] else CHANGED


def merge_baseline(old: dict, fresh: dict, order: list) -> tuple[list, list]:
    """Put freshly fetched entries into a baseline. Returns (entries, kept).

    A refresh never throws away a hash it cannot replace: if a source was
    blocked or unreachable this time and the old entry holds a hash for
    the same address, the old entry stays, whatever rules it was written
    under. "kept" lists those ids. A hash under other rules is still never
    compared; it is kept so it can be carried forward or checked against
    the next whole fetch. Sources that left the registry are dropped.
    """
    entries, kept = [], []
    for source_id in order:
        new, was = fresh.get(source_id), old.get(source_id)
        if new is None:
            if was:
                entries.append(was)
            continue
        if new["sha256"] is None and (has_baseline(was, new["url"]) or older_rules(was, new["url"])):
            entries.append(was)
            kept.append(source_id)
        else:
            entries.append(new)
    return entries, kept


def compared_with_earlier(was: dict | None, result: dict, url: str, old_text: str | None) -> str | None:
    """For a fresh fetch of url about to replace a stored hash: whether it
    says what that hash said, under the rules the hash was taken under.
    old_text is the saved text of the earlier fetch, if it is on hand. None
    if there is nothing to compare (no earlier hash for this address, or
    nothing fetched)."""
    if result.get("state") != FETCHED or not was or not was.get("sha256") or was.get("url") != url:
        return None
    when = f"the entry of {was['fetched']} (rules {was.get('rules', 1)})"
    if was.get("mode") != result.get("mode"):
        return f"different from {when}: compared as {was.get('mode')} then, {result.get('mode')} now"
    if result["mode"] == "bytes":
        same = result["sha256"] == was["sha256"]
    elif was.get("rules") == RULES:
        same = result["sha256"] == was["sha256"]
    elif old_text is not None and text_digest(old_text, was.get("rules", 1)) == was["sha256"]:
        same = text_digest(old_text) == result["sha256"]
    else:
        return f"not known: the text behind {when} is not on hand"
    return f"the same as {when}" if same else f"different from {when}"


def carry_forward(entry: dict | None, text: str | None) -> tuple[dict | None, str | None]:
    """Re-hash a baseline entry under the current rules, from the text it
    was made from, without asking the source again. Returns (entry, None),
    or (None, why not). The words that were baselined stay the baseline;
    nothing the source says now is taken in. A bytes entry is never
    carried forward: there is no saved copy to re-take its hash from, and
    whether that reply was whole is not known."""
    if not entry or not entry.get("sha256"):
        return None, "it has no stored hash"
    if entry.get("rules") == RULES:
        return None, "it is already under the current rules"
    if entry.get("mode") == "bytes":
        return None, ("it is compared by its bytes, which are not saved, so its hash cannot be re-taken "
                      "and whether that reply was whole is not known")
    if text is None or text_digest(text, entry.get("rules", 1)) != entry["sha256"]:
        return None, "the text the baseline hashed is not on hand on this computer"
    why = not_the_source("text", text)
    if why:
        return None, "the baseline text is not the source: " + why
    return {**entry, "sha256": text_digest(text), "length": len(canonical(text)), "rules": RULES,
            "carried": f"re-hashed under rules {RULES} from the text fetched on {entry['fetched']}"}, None


def bounded_diff(old: str, new: str, limit: int = DIFF_LINES, width: int = DIFF_LINE_CHARS) -> str:
    """What changed between two texts, cut to a fixed size.

    The words are compared, not the lines, so a line that was only joined
    to the next or split in two is never shown as a change. For each
    change, the lines that hold the changed words are shown: "-" from the
    baseline, "+" from now.
    """
    def words_and_lines(text):
        lines = text.splitlines()
        words, line_of = [], []
        for number, line in enumerate(lines):
            for word in canonical(line).split():
                words.append(word)
                line_of.append(number)
        return words, line_of, lines

    old_words, old_line_of, old_lines = words_and_lines(old)
    new_words, new_line_of, new_lines = words_and_lines(new)

    def lines_for(line_of, start, end):
        if start < end:
            return list(range(line_of[start], line_of[end - 1] + 1))
        # No words on this side. If the change sits inside one line, show that
        # line, so a word added mid-sentence shows the sentence before and after.
        if 0 < start < len(line_of) and line_of[start - 1] == line_of[start]:
            return [line_of[start]]
        return []

    out = []
    matcher = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False)
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        before = " ".join(old_words[max(0, a1 - 6):a1])
        out.append(f"@@ after: {before} @@" if before else "@@ at the start @@")
        out += ["-" + old_lines[n] for n in lines_for(old_line_of, a1, a2)]
        out += ["+" + new_lines[n] for n in lines_for(new_line_of, b1, b2)]
    shown = [line if len(line) <= width else line[:width] + " [cut]" for line in out[:limit]]
    if len(out) > limit:
        shown.append(f"[{len(out) - limit} more diff lines not shown]")
    # Three backticks in a source would end the report's code block early.
    return "\n".join(shown).replace("```", "'''")

# The comparison rules (end)
# ===========================================================================


# Lines that change on every load of a page, for reasons that have nothing to
# do with what the page says, by source id. The comparison rules above read
# this list. Each one was seen to flip between two fetches a
# few minutes apart. They are dropped from that source's text before hashing,
# and the baseline entry says so. Keep this list short, and add to it only
# after seeing a line flip with no change a reader would notice.
VOLATILE = {
    # A server name at the foot of the page ("N1", "N2").
    "wa-courts-forms": {"lines": [r"N\d{1,2}"], "why": "the server's name at the foot of the page (N1, N2)"},
    # The contact form's hidden spam trap gets a random label ("Name", "Comments").
    "us-lambda-helpdesk": {
        "before": ["This field is for validation purposes and should be left unchanged."],
        "why": "the random label of the contact form's hidden spam-trap field",
    },
}


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
CUT_SHORT = (http.client.IncompleteRead, http.client.RemoteDisconnected, ConnectionResetError, CutShort)


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
                return examine(body, response.headers.get("Content-Type", "") or "",
                               response.headers.get("Content-Length"))
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
        result = apply_volatile(fetcher(url), src["id"])
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
    """The baseline as {source id: entry}. A missing or empty file is an empty baseline.
    Retired entries (marked with a retired date) stay in the file but are
    not part of the active baseline."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    out = {}
    for entry in data:
        entry = dict(entry)
        if entry.get("retired"):
            continue
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
    if result.get("sha256"):
        entry["rules"] = RULES
    if result.get("note"):
        entry["note"] = result["note"]
    return entry


def dump_baseline(entries: list, today: str | None = None) -> str:
    """The baseline file's text: the header, then one block per source.
    With a date, the header carries the file's written date (B5)."""
    blocks = []
    for entry in entries:
        clean = {k: v for k, v in entry.items() if v is not None}
        for key in ("fetched", "registry_checked", "retired"):
            if key in clean and isinstance(clean[key], str):
                clean[key] = dt.date.fromisoformat(clean[key])
        blocks.append(yaml.safe_dump([clean], sort_keys=False, allow_unicode=True, width=1000))
    header = BASELINE_HEADER
    if today:
        header += f"# written: {today}\n"
    return header + "\n" + "\n".join(blocks)


def save_baseline(path: Path, entries: list, today: str | None = None):
    path.write_text(dump_baseline(entries, today), encoding="utf-8")


def save_baseline_guarded(path: Path, entries: list, today: str, baseline: dict,
                          registry: list, accepted: dict) -> bool:
    """Write a baseline through the Stage A guard (tests/guards.py).

    Prints the completeness diff either way. If any invariant fails,
    writes nothing and returns False; the caller exits 3. Entries for
    sources that left the registry stay in the file, marked retired
    with their hashes, instead of being dropped (B1)."""
    registry_urls = {src["id"]: src["url"] for src in registry}
    new = {entry["id"]: entry for entry in entries}
    _, old_written, prior_retired = guards.load_baseline_file(path)
    retired = {entry["id"]: entry for entry in prior_retired}
    for source_id, entry in baseline.items():
        if source_id not in registry_urls and source_id not in new:
            retired[source_id] = {**entry, "retired": today}
    for line in guards.completeness_diff(baseline, new, retired, RULES, "Strand", today):
        print(line)
    reasons = guards.check_invariants(baseline, new, registry_urls, retired, old_written,
                                      today, RULES, accepted, "GITHUB_ACTIONS" in os.environ)
    if reasons:
        for reason in reasons:
            print(f"Refused: {reason}", file=sys.stderr)
        return False
    full = entries + [retired[source_id] for source_id in sorted(retired)]
    text = dump_baseline(full, today)
    backup = os.environ.get("GUARDS_BACKUP_DIR")
    guards.atomic_write(path, text, guards.parse_baseline_text, guards._norm(full),
                        Path(backup) if backup else None, today)
    return True


def snapshot_path(folder: Path, source_id: str) -> Path:
    return folder / (re.sub(r"[^A-Za-z0-9._-]", "_", source_id) + ".txt")


def save_snapshot(folder: Path, source_id: str, text: str | None):
    if text is None:
        return
    folder.mkdir(parents=True, exist_ok=True)
    snapshot_path(folder, source_id).write_text(text, encoding="utf-8")


def load_snapshot(folder: Path, source_id: str, digest: str, rules: int = RULES) -> str | None:
    """The saved text for a source, only if it is the text the baseline hashed."""
    path = snapshot_path(folder, source_id)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return text if text_digest(text, rules) == digest else None


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
        if older_rules(entry, src["url"]):
            return "Its baseline was written under older comparison rules, so it has none to compare with."
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
        why = ("its address changed since the baseline" if moved else
               "its baseline was written under older comparison rules" if older_rules(baseline.get(src["id"]), src["url"])
               else "no stored hash")
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
    parser.add_argument("--carry-forward", action="store_true",
                        help="re-hash baseline entries written under older comparison rules from their saved "
                             "text, without fetching anything")
    parser.add_argument("--only", nargs="+", metavar="ID", help="only these source ids")
    parser.add_argument("--results", type=Path, help="also write the run as JSON, for tests/mechanical_update.py")
    parser.add_argument("--baseline", type=Path, default=BASELINE, help="the baseline file (for tests)")
    parser.add_argument("--registry", type=Path, default=REGISTRY, help="a sources file (for tests)")
    parser.add_argument("--facts", type=Path, default=FACTS, help="a facts file (for tests)")
    parser.add_argument("--build-report", type=Path, default=BUILD_REPORT, help="a build report (for tests)")
    parser.add_argument("--snapshots", type=Path, default=SNAPSHOTS,
                        help="folder for the text of each web page, used to show what changed; not committed")
    parser.add_argument("--today", help="YYYY-MM-DD, for testing")
    parser.add_argument("--accept-change", action="append", default=[], metavar="ID",
                        help="accept that this source's hash changed (repeatable); needs --reason; "
                             "refused when GITHUB_ACTIONS is set")
    parser.add_argument("--reason", help="why the --accept-change hashes changed; recorded nowhere "
                                         "but required, so the acceptance is a deliberate act")
    args = parser.parse_args(argv)
    today = args.today or dt.date.today().isoformat()
    if bool(args.accept_change) != bool(args.reason):
        print("--accept-change and --reason go together.", file=sys.stderr)
        return 2
    accepted = {source_id: args.reason for source_id in args.accept_change}

    registry = load_sources(args.registry)
    entries = registry
    if args.only:
        unknown = sorted(set(args.only) - {src["id"] for src in registry})
        if unknown:
            print(f"Not in data/sources.yml: {', '.join(unknown)}", file=sys.stderr)
            return 2
        entries = [src for src in registry if src["id"] in args.only]
    baseline = load_baseline(args.baseline)
    if args.write_baseline and args.carry_forward:
        print("Use --write-baseline or --carry-forward, not both.", file=sys.stderr)
        return 2

    if args.carry_forward:
        carried, left = {}, []
        for src in entries:
            was = baseline.get(src["id"])
            path = snapshot_path(args.snapshots, src["id"])
            text = path.read_text(encoding="utf-8") if path.exists() else None
            new, why = carry_forward(was, text)
            if new and new["url"] != src["url"]:
                new, why = None, "its address changed since the baseline"
            if new:
                carried[src["id"]] = new
                print(f"{src['id']}: carried forward ({new['carried']})", flush=True)
            elif was and was.get("sha256") and why != "it is already under the current rules":
                left.append(src["id"])
                print(f"{src['id']}: not carried forward ({why})", flush=True)
        merged = [carried.get(source_id, entry) for source_id, entry in baseline.items()]
        if not save_baseline_guarded(args.baseline, merged, today, baseline, registry, accepted):
            return 3
        print(f"\nWrote {args.baseline} ({len(carried)} entries carried forward to rules {RULES}).")
        if left:
            print("  Not carried forward; these need --write-baseline, which says whether each still says what "
                  "its earlier hash said (if not, a person reads it first): " + ", ".join(left))
        return 0

    if args.write_baseline:
        fresh, counts = {}, {}
        for src, result in fetch_all(entries, fetcher=fetcher, robots=robots):
            fresh[src["id"]] = baseline_entry(src, result, today)
            counts[result["state"]] = counts.get(result["state"], 0) + 1
            was = baseline.get(src["id"])
            if result["state"] == FETCHED:
                # Read the earlier text before this fetch's text takes its place.
                old_text = (load_snapshot(args.snapshots, src["id"], was["sha256"], was.get("rules", 1))
                            if was and was.get("sha256") and was.get("mode") == "text" else None)
                earlier = compared_with_earlier(was, result, src["url"], old_text)
                if earlier:
                    fresh[src["id"]]["earlier"] = earlier
                save_snapshot(args.snapshots, src["id"], result["text"])
            print(f"{src['id']}: {result['state']}" + (f" ({result['note']})" if result.get("note") else "")
                  + (f"; {fresh[src['id']]['earlier']}" if fresh[src["id"]].get("earlier") else ""), flush=True)
        merged, kept = merge_baseline(baseline, fresh, [src["id"] for src in registry])
        if not save_baseline_guarded(args.baseline, merged, today, baseline, registry, accepted):
            return 3
        print(f"\nWrote {args.baseline} ({len(merged)} entries; {len(fresh)} fetched in this run).")
        for state in (FETCHED, BLOCKED, UNREACHABLE):
            print(f"  {state}: {counts.get(state, 0)}")
        modes = [entry["mode"] for entry in fresh.values() if entry["mode"]]
        print(f"  compared as text: {modes.count('text')}; as bytes: {modes.count('bytes')}")
        if kept:
            print("  Kept the earlier hash for sources that could not be read this time: " + ", ".join(kept))
        for label, start in (("Says the same as its earlier hash", "the same"),
                             ("Says something different from its earlier hash; a person reads these before the "
                              "new hash is relied on", "different"),
                             ("Could not be compared with its earlier hash (the earlier text is not on hand)",
                              "not known")):
            ids = [source_id for source_id, item in fresh.items() if item.get("earlier", "").startswith(start)]
            if ids:
                print(f"  {label}: {', '.join(ids)}")
        first = [source_id for source_id, item in fresh.items() if item.get("sha256") and not item.get("earlier")]
        if first:
            print("  A first hash, with no earlier one to compare (a person reads these first): " + ", ".join(first))
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

    scope = {src["id"]: src["url"] for src in entries}
    unreconciled = guards.ledger2(scope, {src["id"]: state for src, _, state in rows}, baseline, RULES)
    if unreconciled:
        for reason in unreconciled:
            print(f"Unreconciled: {reason}", file=sys.stderr)
        return 3

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
