#!/usr/bin/env python3
"""Check color contrast for every theme in static/css/site.css.

Reads the color tokens straight from the CSS, so the numbers in the docs can
never drift from the real stylesheet. Uses the WCAG 2.2 contrast formula.

Targets:
  body text pairs   7.0:1  (WCAG AAA, our goal for all reading text)
  large-text pairs  4.5:1  (AAA for large bold text, used for callout titles)
  UI borders        3.0:1  (WCAG 1.4.11 non-text contrast)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CSS = Path(__file__).resolve().parent.parent / "static" / "css" / "site.css"

TEXT_PAIRS = [
    ("text", "bg"), ("text", "surface"), ("heading", "bg"), ("heading", "surface"),
    ("link", "bg"), ("link", "surface"), ("link-visited", "bg"), ("link-visited", "surface"),
    ("header-text", "header-bg"), ("header-accent", "header-bg"),
    ("text", "why-bg"), ("heading", "why-bg"), ("link", "why-bg"), ("link-visited", "why-bg"),
    ("text", "watch-bg"), ("link", "watch-bg"), ("link-visited", "watch-bg"),
    ("text", "changed-bg"), ("link", "changed-bg"), ("link-visited", "changed-bg"), ("heading", "changed-bg"),
    ("text", "cost-bg"), ("link", "cost-bg"), ("link-visited", "cost-bg"), ("heading", "cost-bg"),
    ("btn-text", "btn-bg"), ("exit-text", "exit-bg"), ("focus-text", "focus-bg"),
    ("link", "badge-bg"), ("text", "badge-bg"), ("text", "code-bg"),
]
LARGE_PAIRS = [("watch-title", "watch-bg"), ("watch-title", "badge-bg")]
UI_PAIRS = [("border", "bg"), ("border", "surface"), ("focus-ring", "bg"), ("focus-ring", "surface")]


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def tokens(block: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in re.finditer(r"--([a-z-]+):\s*(#[0-9A-Fa-f]{3,6})", block)}


def main() -> int:
    css = CSS.read_text(encoding="utf-8")

    def block_after(selector_regex: str) -> str:
        m = re.search(selector_regex + r"\s*\{(.*?)\n\}", css, flags=re.S)
        if not m:
            raise SystemExit(f"could not find block {selector_regex}")
        return m.group(1)

    light = tokens(block_after(r':root,\s*html\[data-theme="light"\]'))
    dark = tokens(block_after(r'html\[data-theme="dark"\]'))
    contrast = tokens(block_after(r'html\[data-theme="contrast"\]'))
    auto_dark = tokens(re.search(r"prefers-color-scheme: dark\)\s*\{\s*html\[data-theme=\"auto\"\]\s*\{(.*?)\}", css, re.S).group(1))

    problems = 0
    # The "match my device" dark theme must be identical to the dark theme.
    for key, value in dark.items():
        if auto_dark.get(key, "").lower() != value.lower():
            print(f"MISMATCH auto-dark --{key}: {auto_dark.get(key)} vs dark {value}")
            problems += 1

    themes = {"light": light, "dark": dark, "high contrast": {**light, **contrast}}
    for name, t in themes.items():
        print(f"\n== {name} ==")
        for pairs, target, kind in ((TEXT_PAIRS, 7.0, "text"), (LARGE_PAIRS, 4.5, "large text"), (UI_PAIRS, 3.0, "UI")):
            for fg, bg in pairs:
                if fg not in t or bg not in t:
                    print(f"  missing token for {fg} on {bg}")
                    problems += 1
                    continue
                r = ratio(t[fg], t[bg])
                ok = r >= target
                flag = "ok  " if ok else "FAIL"
                print(f"  {flag} {fg:13s} on {bg:11s} {t[fg]} / {t[bg]}  {r:5.2f}:1  (need {target} for {kind})")
                if not ok:
                    problems += 1
    print(f"\n{problems} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
