#!/usr/bin/env python3
"""Real-browser checks with Playwright (Chromium).

Run after build.py:  python3 tests/browser_checks.py

Checks every page for:
- JavaScript errors and Content Security Policy violations
- no sideways scrolling at 320px wide (the width of a 1280px screen at 400% zoom)
- no sideways scrolling with WCAG 1.4.12 text spacing applied
- buttons, form controls, menus, and summaries at least 24 by 24 px (WCAG 2.5.8)
- a visible focus style on the first tab stops
Then tests the path finder, Reading settings, Leave quickly, checklists,
and the page with JavaScript turned off.
"""
from __future__ import annotations

import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

PUBLIC = Path(__file__).resolve().parent.parent / "public"
SPACING_CSS = (
    "* { line-height: 1.5 !important; letter-spacing: 0.12em !important; "
    "word-spacing: 0.16em !important; } p { margin-bottom: 2em !important; }"
)
problems: list[str] = []

OBSCURED_JS = """() => {
  const isInline = e => getComputedStyle(e).display === 'inline';
  const inText = e => {
    if (!isInline(e)) return false;
    let p = e.parentElement;
    while (p && getComputedStyle(p).display.startsWith('inline')) p = p.parentElement;
    const all = (p.textContent || '').replace(/\\s+/g, '');
    let widgets = '';
    p.querySelectorAll('a[href],button,input,summary,select').forEach(x => widgets += (x.textContent || ''));
    return all.length > widgets.replace(/\\s+/g, '').length;
  };
  const visible = e => {
    const r = e.getBoundingClientRect();
    return r.width > 0 && r.height > 0 && !e.closest('dialog:not([open])') && !e.closest('[hidden]')
      && !e.classList.contains('skip-link') && !(e.closest('details:not([open])') && !e.matches('summary'));
  };
  const targets = [...document.querySelectorAll('a[href],button,input,summary,select')].filter(visible);
  const out = [];
  targets.forEach(e => {
    if (inText(e)) return;
    const r = e.getBoundingClientRect();
    targets.forEach(o => {
      if (o === e || o.contains(e) || e.contains(o)) return;
      const q = o.getBoundingClientRect();
      const ix = Math.min(r.right, q.right) - Math.max(r.left, q.left);
      const iy = Math.min(r.bottom, q.bottom) - Math.max(r.top, q.top);
      if (ix > 0 && iy > 0 && r.height - iy < 24 && r.width - ix < 24) {
        out.push(e.tagName + ' "' + (e.textContent || '').trim().slice(0, 30) + '" under ' + o.tagName + ' "' + (o.textContent || '').trim().slice(0, 30) + '"');
      }
    });
  });
  return out;
}"""


def fail(msg: str) -> None:
    problems.append(msg)
    print("  FAIL", msg)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep test output readable
        pass


def serve() -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(PUBLIC))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def main() -> int:
    httpd, port = serve()
    base = f"http://127.0.0.1:{port}/"
    pages = sorted(p.name for p in PUBLIC.glob("*.html"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        ctx.route("https://www.weather.gov/**", lambda r: r.fulfill(status=200, body="<title>Weather</title>weather", content_type="text/html"))
        page = ctx.new_page()
        # A second context that ignores the Content Security Policy, only so the
        # test can inject the WCAG text-spacing styles.
        spacing_ctx = browser.new_context(viewport={"width": 320, "height": 800}, bypass_csp=True)
        spacing_page = spacing_ctx.new_page()
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))

        for name in pages:
            print(f"- {name}")
            errors.clear()
            page.set_viewport_size({"width": 1280, "height": 900})
            page.goto(base + name)
            page.wait_for_load_state("load")
            if errors:
                fail(f"{name}: console errors: {errors[:3]}")

            # Visible focus on the first tab stops.
            page.keyboard.press("Tab")
            for i in range(12):
                info = page.evaluate("""() => {
                    const el = document.activeElement;
                    if (!el || el === document.body) return null;
                    const s = getComputedStyle(el);
                    return {tag: el.tagName, text: (el.textContent || '').trim().slice(0, 40),
                            outline: s.outlineStyle !== 'none' && parseFloat(s.outlineWidth) >= 2,
                            shadow: s.boxShadow !== 'none',
                            bg: s.backgroundColor};
                }""")
                if info and not (info["outline"] or info["shadow"]):
                    fail(f"{name}: no visible focus on tab stop {i + 1}: {info}")
                    break
                page.keyboard.press("Tab")

            # Reflow at 320px.
            page.set_viewport_size({"width": 320, "height": 800})
            page.goto(base + name)
            overflow = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            if overflow > 1:
                fail(f"{name}: scrolls sideways by {overflow}px at 320px wide")
            spacing_page.goto(base + name)
            spacing_page.add_style_tag(content=SPACING_CSS)
            overflow = spacing_page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            if overflow > 1:
                fail(f"{name}: scrolls sideways by {overflow}px with text spacing at 320px")

            # Target size, 24px minimum, for non-inline controls.
            small = page.evaluate("""() => {
                const out = [];
                document.querySelectorAll('button, input, select, summary, .site-nav a, .footer-links a, .btn, .btn-secondary, .exit-link').forEach(el => {
                    const r = el.getBoundingClientRect();
                    if (r.width === 0 && r.height === 0) return;
                    if (getComputedStyle(el).visibility === 'hidden') return;
                    if (el.closest('dialog:not([open])') || el.closest('[hidden]')) return;
                    if (r.width < 24 || r.height < 24) out.push(el.tagName + ' ' + (el.textContent || el.name || '').trim().slice(0, 30) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
                });
                return out;
            }""")
            if small:
                fail(f"{name}: targets under 24px: {small[:5]}")

            # Obscured targets, the way axe-core's target-size rule sees them:
            # a standalone control (not a link inside a sentence) fails when another
            # target's bounding box covers it so that no 24 by 24 px area is left.
            # A wrapped inline link's bounding box spans every line it touches.
            obscured = page.evaluate(OBSCURED_JS)
            if obscured:
                fail(f"{name}: targets covered by a neighbor's box: {obscured[:3]}")

        # ---- Focus not hidden under the sticky Leave quickly bar (WCAG 2.4.11) ----
        print("- focus not obscured")
        for width in (1280, 320):
            page.set_viewport_size({"width": width, "height": 700})
            page.goto(base + "oregon.html")
            for i in range(45):
                page.keyboard.press("Tab")
                hidden = page.evaluate("""() => {
                    const el = document.activeElement;
                    const bar = document.querySelector('.exit-bar');
                    if (!el || el === document.body || !bar || bar.contains(el) || el.classList.contains('skip-link')) return false;
                    const r = el.getBoundingClientRect();
                    const b = bar.getBoundingClientRect();
                    return r.bottom <= b.bottom + 1;
                }""")
                if hidden:
                    fail(f"focus hidden under the sticky bar at {width}px, tab stop {i + 1}")
                    break

        # ---- Path finder ----
        print("- path finder")
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(base + "path.html")
        page.click("#path-form button[type=submit]")
        if not page.is_visible("#path-error"):
            fail("path finder: no error when submitted empty")
        focused = page.evaluate("() => document.activeElement && document.activeElement.name")
        if focused != "live":
            fail(f"path finder: focus should go to the first missing question, went to {focused}")
        for q, v in (("live", "or"), ("change", "both"), ("who", "adult"), ("born", "wa")):
            page.check(f'input[name="{q}"][value="{v}"]')
        page.click("#path-form button[type=submit]")
        if not page.is_visible("#path-results"):
            fail("path finder: results did not appear")
        blocks = page.locator("#results-body .result-block").count()
        if blocks < 5:
            fail(f"path finder: expected at least 5 result blocks, got {blocks}")
        if page.evaluate("() => document.activeElement.id") != "results-h":
            fail("path finder: focus did not move to the results heading")
        text = page.inner_text("#results-body")
        if "DOH 422-143" not in text or "any Oregon circuit court" not in text:
            fail("path finder: expected Oregon court and Washington birth certificate steps")
        if "DOH 422-144" in text:
            fail("path finder: minor-only line shown for an adult")
        # A parent in Utah asking for a marker change sees the age rule.
        page.click("#path-form button[type=reset]")
        for q, v in (("live", "ut"), ("change", "marker"), ("who", "parent"), ("born", "ut")):
            page.check(f'input[name="{q}"][value="{v}"]')
        page.click("#path-form button[type=submit]")
        if "15 years and 6 months" not in page.inner_text("#results-body"):
            fail("path finder: Utah minor rule missing for a parent")

        # ---- Reading settings ----
        print("- reading settings")
        page.goto(base + "index.html")
        page.click("#settings-open")
        if not page.evaluate("() => document.getElementById('settings').open"):
            fail("settings: dialog did not open")
        page.check('#settings input[name="theme"][value="dark"]')
        if page.evaluate("() => document.documentElement.dataset.theme") != "dark":
            fail("settings: dark theme not applied")
        page.check('#settings input[name="brief"]')
        page.click("#settings-close")
        if page.evaluate("() => document.activeElement.id") != "settings-open":
            fail("settings: focus did not return to the settings button")
        stored = page.evaluate("() => { try { return localStorage.getItem('strand:prefs'); } catch (e) { return 'error'; } }")
        if stored:
            fail("settings: saved to the device without 'Remember' turned on")
        page.goto(base + "oregon.html")
        if page.evaluate("() => document.documentElement.dataset.theme") == "dark":
            fail("settings: theme persisted without 'Remember' turned on")

        # ---- Checklist ----
        print("- checklist")
        page.goto(base + "oregon.html")
        box = page.locator('input[data-check="oregon:or-step-forms"]')
        box.check()
        if "is-done" not in (page.get_attribute("#or-step-forms", "class") or ""):
            fail("checklist: step not marked done")

        # ---- Leave quickly ----
        print("- leave quickly")
        page.goto(base + "oregon.html")
        page.click("#quick-exit")
        page.wait_for_url("https://www.weather.gov/**", timeout=5000)
        page.goto(base + "index.html")
        page.locator("body").click(position={"x": 5, "y": 300})
        for _ in range(3):
            page.keyboard.press("Shift")
        try:
            page.wait_for_url("https://www.weather.gov/**", timeout=5000)
        except Exception:
            fail("leave quickly: Shift x3 did not leave the page")

        # ---- No JavaScript ----
        print("- javascript off")
        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        p2 = nojs.new_page()
        p2.goto(base + "path.html")
        if not p2.is_visible(".no-js-only"):
            fail("no-js: fallback links not shown on the path page")
        if p2.is_visible("#path-form"):
            fail("no-js: path form shown even though it cannot work")
        p2.goto(base + "oregon.html")
        if p2.is_visible("#settings-open"):
            fail("no-js: settings button shown even though it cannot work")
        if not p2.is_visible("#steps"):
            fail("no-js: content missing")
        browser.close()
    httpd.shutdown()
    print(f"\n{len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
