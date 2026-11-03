#!/usr/bin/env python3
"""Estimate the reading grade level of each page's main content.

Uses the Flesch-Kincaid grade formula with a simple syllable counter, so the
numbers are estimates. Source labels, badges, the page source list, and the
"On this page" menu are left out. Each list item, heading, cell, and paragraph
counts as its own sentence.

Exit 1 if any page is above FAIL_ABOVE. Pages above GOAL get a warning.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "public"
GOAL = 8.0
FAIL_ABOVE = 10.0
LONG_SENTENCE = 25  # words; listed as warnings so a person can shorten them
SKIP_CLASSES = {"page-sources", "src", "badge", "toc", "kicker", "checked", "copy-btn", "vh", "step-num"}
BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "dt", "dd", "summary", "caption", "legend", "label"}
SKIP_TAGS = {"script", "style", "template"}


class MainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.skip_depth = 0
        self.stack: list[bool] = []
        self.chunks: list[str] = []
        self.current = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "main":
            self.in_main = True
        classes = set((a.get("class") or "").split())
        skip = tag in SKIP_TAGS or bool(classes & SKIP_CLASSES) or a.get("hidden") is not None
        if tag not in {"br", "input", "img", "hr", "meta", "link"}:
            self.stack.append(skip)
            if skip:
                self.skip_depth += 1
        if tag in BLOCKS:
            self.flush()

    def handle_endtag(self, tag):
        if tag in BLOCKS:
            self.flush()
        if tag == "main":
            self.in_main = False
        if self.stack and tag not in {"br", "input", "img", "hr", "meta", "link"}:
            if self.stack.pop():
                self.skip_depth -= 1

    def handle_data(self, data):
        if self.in_main and self.skip_depth == 0:
            self.current += data

    def flush(self):
        text = re.sub(r"\s+", " ", self.current).strip()
        if text:
            if text[-1] not in ".!?:":
                text += "."
            self.chunks.append(text)
        self.current = ""


def syllables(word: str) -> int:
    w = word.lower()
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    groups = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(groups))


def grade(text: str) -> tuple[float, int, int]:
    sentences = [s for s in re.split(r"(?<=[.!?:])\s+", text) if re.search(r"[A-Za-z]", s)]
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", text)
    if not sentences or not words:
        return 0.0, 0, 0
    syl = sum(syllables(w) for w in words)
    g = 0.39 * (len(words) / len(sentences)) + 11.8 * (syl / len(words)) - 15.59
    return g, len(words), len(sentences)


def main() -> int:
    worst = 0
    failed = []
    print(f"Goal: grade {GOAL:.0f} or lower. Fails above grade {FAIL_ABOVE:.0f}.\n")
    for page in sorted(PUBLIC.glob("*.html")):
        parser = MainText()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.flush()
        g, words, sents = grade(" ".join(parser.chunks))
        worst = max(worst, g)
        mark = "ok  " if g <= GOAL else ("warn" if g <= FAIL_ABOVE else "FAIL")
        if g > FAIL_ABOVE:
            failed.append(page.name)
        print(f"{mark} {page.name:20s} grade {g:4.1f}  ({words} words, {sents} sentences)")
        text = " ".join(parser.chunks)
        for s in re.split(r"(?<=[.!?:])\s+", text):
            n = len(re.findall(r"[A-Za-z][A-Za-z'\-]*", s))
            if n > LONG_SENTENCE:
                print(f"       long sentence ({n} words): {s[:110]}...")
    print(f"\nHighest grade: {worst:.1f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
