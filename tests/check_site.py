#!/usr/bin/env python3
"""Structural checks on the built site in public/.

Fails (exit 1) on:
- a page without lang, title, or exactly one h1
- heading levels that skip (for example h2 straight to h4)
- duplicate ids on a page
- internal links or #anchors that point nowhere
- links without text, buttons without a name, form fields without a label
- inline scripts, inline styles, or on* handlers (the Content Security Policy blocks them)
- external links without rel="noreferrer"
- unclosed or mismatched tags
- a Content Security Policy meta tag that differs from public/_headers, or
  security headers that differ from the set shared with The Stasis Project
  (docs/decisions/ADR-0010-shared-with-stasis.md)
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

PUBLIC = Path(__file__).resolve().parent.parent / "public"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
# Elements whose end tags HTML lets you leave out. We still close ours, but
# do not treat a missing one as fatal.
OPTIONAL_END = {"li", "p", "dt", "dd", "tr", "td", "th", "option", "thead", "tbody"}

# The same headers The Stasis Project sends (ADR-0010). Change both projects
# together, or record the difference there.
SHARED_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
    "connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'"
)
SHARED_HEADERS = {
    "Content-Security-Policy": SHARED_CSP + "; frame-ancestors 'none'",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "accelerometer=(), browsing-topics=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.ids: list[str] = []
        self.headings: list[int] = []
        self.links: list[tuple[str, dict]] = []
        self.lang = None
        self.meta_csp = None
        self.title = ""
        self.in_title = False
        self.label_for: set[str] = set()
        self.fields: list[dict] = []
        self.open_label = 0
        self.open_template = 0
        self.text_target: list[dict] = []   # elements collecting text (a, button)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "content-security-policy":
            self.meta_csp = a.get("content") or ""
        if "id" in a:
            self.ids.append(a["id"])
        for name in a:
            if name.startswith("on"):
                self.errors.append(f"inline event handler '{name}' on <{tag}>")
        if "style" in a:
            self.errors.append(f"inline style attribute on <{tag}>")
        if tag == "script" and "src" not in a:
            self.errors.append("inline <script> (blocked by the Content Security Policy)")
        if tag == "style":
            self.errors.append("inline <style> (blocked by the Content Security Policy)")
        if tag == "title":
            self.in_title = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and not self.open_template:
            self.headings.append(int(tag[1]))
        if tag == "template":
            self.open_template += 1
        if tag == "label":
            self.open_label += 1
            if "for" in a:
                self.label_for.add(a["for"])
        if tag in {"input", "select", "textarea"} and a.get("type") not in {"hidden", "submit", "reset", "button"}:
            self.fields.append({"id": a.get("id"), "in_label": self.open_label > 0, "aria": a.get("aria-label") or a.get("aria-labelledby")})
        if tag in {"a", "button"}:
            entry = {"tag": tag, "attrs": a, "text": ""}
            self.text_target.append(entry)
            if tag == "a":
                self.links.append((a.get("href", ""), a))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag == "label":
            self.open_label -= 1
        if tag == "template":
            self.open_template -= 1
        if tag in {"a", "button"} and self.text_target:
            entry = self.text_target.pop()
            name = entry["text"].strip() or entry["attrs"].get("aria-label", "").strip()
            if not name:
                self.errors.append(f"<{tag}> with no accessible name: {entry['attrs']}")
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
            return
        # Allow omitted optional end tags.
        while self.stack and self.stack[-1] in OPTIONAL_END and self.stack[-1] != tag:
            self.stack.pop()
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"mismatched </{tag}>; open: {self.stack[-3:]}")

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        for entry in self.text_target:
            entry["text"] += data


def check_page(path: Path, all_ids: dict[str, set[str]]) -> list[str]:
    p = PageParser()
    p.feed(path.read_text(encoding="utf-8"))
    errs = list(p.errors)
    if not p.lang:
        errs.append("missing <html lang>")
    if not p.title.strip():
        errs.append("missing <title>")
    h1 = p.headings.count(1)
    if h1 != 1:
        errs.append(f"expected 1 <h1>, found {h1}")
    prev = 0
    for level in p.headings:
        if prev and level > prev + 1:
            errs.append(f"heading skips from h{prev} to h{level}")
        prev = level
    dupes = {i for i in p.ids if p.ids.count(i) > 1}
    if dupes:
        errs.append(f"duplicate ids: {sorted(dupes)}")
    leftover = [t for t in p.stack if t not in OPTIONAL_END]
    if leftover:
        errs.append(f"unclosed tags: {leftover}")
    for f in p.fields:
        if not (f["in_label"] or (f["id"] and f["id"] in p.label_for) or f["aria"]):
            errs.append(f"form field without a label: {f}")
    for href, attrs in p.links:
        if not href:
            errs.append(f"link without href: {attrs}")
            continue
        u = urlparse(href)
        if u.scheme in {"http", "https"}:
            if "noreferrer" not in (attrs.get("rel") or ""):
                errs.append(f"external link without rel=noreferrer: {href}")
            continue
        if u.scheme in {"mailto", "tel"}:
            continue
        target = path.name if not u.path else u.path.lstrip("/").split("/")[-1]
        if path.name == "404.html" and u.path.startswith("/"):
            target = u.path.rstrip("/").split("/")[-1] or "index.html"
        if u.path and target in {"", "."}:
            target = "index.html"            # "./" or "/" means the home page
        if target not in all_ids and f"{target}.html" in all_ids:
            target = f"{target}.html"        # clean URLs: "oregon" serves oregon.html
        if target not in all_ids:
            errs.append(f"broken internal link: {href}")
            continue
        if u.fragment and u.fragment not in all_ids[target]:
            errs.append(f"missing anchor: {href}")
    return errs


def check_headers() -> list[str]:
    """public/_headers sends exactly the shared headers for every path."""
    path = PUBLIC / "_headers"
    if not path.exists():
        return ["public/_headers is missing"]
    sent: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith((" ", "\t")) and ":" in line:
            name, _, value = line.strip().partition(":")
            sent[name.strip()] = value.strip()
    errors = []
    for name, value in SHARED_HEADERS.items():
        if sent.get(name) != value:
            errors.append(f"{name} should be {value!r}, found {sent.get(name)!r}")
    for name in sent:
        if name not in SHARED_HEADERS:
            errors.append(f"{name} is not in the shared header set (ADR-0010)")
    return errors


def main() -> int:
    pages = sorted(PUBLIC.glob("*.html"))
    if not pages:
        print("No pages in public/. Run build.py first.")
        return 1
    all_ids: dict[str, set[str]] = {}
    for page in pages:
        pp = PageParser()
        pp.feed(page.read_text(encoding="utf-8"))
        all_ids[page.name] = set(pp.ids)
    for extra in ("sources.json", "facts.json", "build-report.json"):
        if (PUBLIC / extra).exists():
            all_ids[extra] = set()
    failed = 0
    header_errors = check_headers()
    if header_errors:
        failed += 1
        print("FAIL _headers")
        for e in header_errors:
            print("   -", e)
    for page in pages:
        errs = check_page(page, all_ids)
        pp = PageParser()
        pp.feed(page.read_text(encoding="utf-8"))
        if pp.meta_csp != SHARED_CSP:
            errs.append(f"Content Security Policy meta tag differs from the shared policy: {pp.meta_csp!r}")
        if errs:
            failed += 1
            print(f"FAIL {page.name}")
            for e in errs:
                print("   -", e)
        else:
            print(f"ok   {page.name}")
    print(f"\n{len(pages) - failed} of {len(pages)} pages passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
