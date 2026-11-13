#!/usr/bin/env python3
"""Real-browser checks with Playwright (Chromium).

Run after build.py:  python3 tests/browser_checks.py

Checks every page for:
- JavaScript errors and Content Security Policy violations
- no sideways scrolling at 320px wide (the width of a 1280px screen at 400% zoom)
- no sideways scrolling with WCAG 1.4.12 text spacing applied
- buttons, form controls, menus, and summaries at least 24 by 24 px (WCAG 2.5.8)
- a visible focus style on the first tab stops
Then tests the path finder, Reading settings, the "How much to show" strip
and Short version mode, Leave quickly, checklists, and the page with
JavaScript turned off.
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
        # Reading settings are saved automatically, as on The Stasis Project (ADR-0010).
        stored = page.evaluate("() => { try { return localStorage.getItem('strand:prefs'); } catch (e) { return 'error'; } }")
        if not stored or '"dark"' not in stored:
            fail("settings: reading settings were not saved on the device")
        page.goto(base + "oregon.html")
        if page.evaluate("() => document.documentElement.dataset.theme") != "dark":
            fail("settings: theme did not carry over to the next page")
        if page.evaluate("() => localStorage.getItem('strand:remember')"):
            fail("settings: 'Remember' turned itself on")
        # "Forget everything" erases saved settings and resets the page.
        page.click("#settings-open")
        page.click("#forget-all")
        page.click("#settings-close")
        left = page.evaluate("() => Object.keys(localStorage).filter(k => k.indexOf('strand:') === 0)")
        if left:
            fail(f"settings: 'Forget everything' left {left}")
        if page.evaluate("() => document.documentElement.dataset.theme") != "auto":
            fail("settings: 'Forget everything' did not reset the colors")

        # ---- "How much to show" strip and Short version mode ----
        print("- short version")
        hidden_sel = ".deeper, .brief-extra"
        shown_js = """sel => [...document.querySelectorAll(sel)].filter(e => e.getClientRects().length > 0).length"""
        state_js = """() => {
            const b = document.getElementById('brief-toggle');
            const vis = e => !!e && e.getClientRects().length > 0;
            const box = document.querySelector('#settings input[name="brief"]');
            let saved = null;
            try { saved = (JSON.parse(localStorage.getItem('strand:prefs') || '{}') || {}).brief || null; } catch (e) {}
            return {
                attr: document.documentElement.getAttribute('data-brief') || 'off',
                pressed: b ? b.getAttribute('aria-pressed') : null,
                label: b ? b.innerText.trim() : null,
                note: vis(document.querySelector('.brief-note')),
                noteText: (document.querySelector('.brief-note') || {}).textContent || '',
                ask: vis(document.querySelector('.brief-ask')),
                hint: vis(document.querySelector('.brief-hint')),
                checkbox: box ? box.checked : null,
                saved: saved,
                focus: document.activeElement ? document.activeElement.id : null,
            };
        }"""

        def expect_state(where: str, on: bool) -> dict:
            st = page.evaluate(state_js)
            want = {
                "attr": "on" if on else "off",
                "pressed": "true" if on else "false",
                "label": "Show the full version" if on else "Show the short version",
                "note": on, "ask": not on, "hint": not on, "checkbox": on,
            }
            for key, value in want.items():
                if st[key] != value:
                    fail(f"short version, {where}: {key} is {st[key]!r}, expected {value!r}")
            return st

        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(base + "index.html")
        page.evaluate("() => localStorage.clear()")
        # The strip is on every page, first thing in the main content, above the
        # page heading, with a button at least 44px tall, and starts in the off state.
        unchanged: list[str] = []
        for name in pages:
            page.goto(base + name)
            info = page.evaluate("""() => {
                const strip = document.querySelector('main .brief-strip');
                const b = document.getElementById('brief-toggle');
                const h1 = document.querySelector('main h1');
                if (!strip || !b || !h1) return null;
                return {
                    count: document.querySelectorAll('.brief-strip').length,
                    visible: strip.getClientRects().length > 0,
                    beforeH1: !!(strip.compareDocumentPosition(h1) & Node.DOCUMENT_POSITION_FOLLOWING),
                    firstInContent: strip === document.querySelector('.content').firstElementChild,
                    isButton: b.tagName === 'BUTTON' && b.type === 'button',
                    height: b.getBoundingClientRect().height,
                };
            }""")
            if not info:
                fail(f"{name}: the How much to show strip, its button, or the h1 is missing")
                continue
            if info["count"] != 1 or not info["visible"] or not info["beforeH1"] or not info["firstInContent"]:
                fail(f"{name}: strip should appear once, visible, first in the main content above the h1: {info}")
            if not info["isButton"] or info["height"] < 44:
                fail(f"{name}: strip control should be a real button at least 44px tall: {info}")
            expect_state(name, False)
            if page.evaluate("sel => document.querySelectorAll(sel).length", hidden_sel) == 0:
                unchanged.append(name)
        print(f"  pages where the short version hides nothing: {', '.join(unchanged) or 'none'}")

        # Keyboard: Enter turns it on. Focus stays on the button, the button does
        # not move in the window, and the change is announced in words.
        page.goto(base + "oregon.html")
        total = page.evaluate("sel => document.querySelectorAll(sel).length", hidden_sel)
        if total < 7 or page.evaluate(shown_js, hidden_sel) != total:
            fail(f"short version: expected the extra sections on the Oregon page to start visible ({total} marked)")
        page.focus("#brief-toggle")
        top_before = page.evaluate("() => document.getElementById('brief-toggle').getBoundingClientRect().top")
        page.keyboard.press("Enter")
        st = expect_state("after Enter on the strip button", True)
        if st["focus"] != "brief-toggle":
            fail(f"short version: focus moved off the strip button to {st['focus']!r}")
        if st["saved"] != "on":
            fail("short version: the strip did not save to the strand:prefs reading settings")
        if "short version" not in st["noteText"] or "Some sections are hidden" not in st["noteText"]:
            fail(f"short version: brief-note does not say sections are hidden: {st['noteText']!r}")
        top_after = page.evaluate("() => document.getElementById('brief-toggle').getBoundingClientRect().top")
        if abs(top_after - top_before) > 1:
            fail(f"short version: the strip button moved {top_after - top_before}px when toggled")
        if page.evaluate(shown_js, hidden_sel) != 0:
            fail("short version: marked sections still visible with the mode on")
        if page.is_visible("#questions") or page.is_visible('.toc a[href="#questions"]'):
            fail("short version: the Good questions heading or its On this page entry is still visible")
        for keep in (".lede", "#steps", "ol.steps", "#or-step-forms", "#cost", "#or-confidential", ".page-sources", ".page-sources ol", "#do-i-need-court + .table-wrap table"):
            if not page.is_visible(keep):
                fail(f"short version: {keep} must stay visible and is hidden")
        page.wait_for_function("() => /Short version\\. .*hidden/.test(document.getElementById('announcer').textContent)", timeout=3000)

        # The dialog checkbox shows the same state, and turning it off there
        # updates the strip.
        page.click("#settings-open")
        expect_state("dialog opened after the strip turned it on", True)
        page.uncheck('#settings input[name="brief"]')
        expect_state("after unchecking the dialog checkbox", False)
        page.check('#settings input[name="brief"]')
        expect_state("after checking the dialog checkbox", True)
        page.click("#settings-close")

        # The saved choice carries to the next page, and the strip's state comes
        # from CSS and prefs.js alone: with site.js blocked it must already show
        # the on wording, so it cannot flash the wrong state while site.js loads.
        ctx.route("**/js/site.js", lambda r: r.abort())
        errors.clear()
        page.goto(base + "washington.html")
        early = page.evaluate("""() => {
            const vis = e => !!e && e.getClientRects().length > 0;
            return {attr: document.documentElement.getAttribute('data-brief'),
                    note: vis(document.querySelector('.brief-note')), ask: vis(document.querySelector('.brief-ask')),
                    label: document.getElementById('brief-toggle').innerText.trim(),
                    shown: [...document.querySelectorAll('.deeper, .brief-extra')].filter(vis).length};
        }""")
        if early != {"attr": "on", "note": True, "ask": False, "label": "Show the full version", "shown": 0}:
            fail(f"short version: wrong state before site.js runs (would flash): {early}")
        ctx.unroute("**/js/site.js")
        errors.clear()   # the blocked script logs one load error, by design
        page.goto(base + "washington.html")
        expect_state("carried to the next page", True)

        # Print always shows everything, and the strip does not print.
        page.goto(base + "oregon.html")
        page.emulate_media(media="print")
        printed = page.evaluate("""sel => {
            const all = [...document.querySelectorAll(sel)];
            return {total: all.length,
                    hidden: all.filter(e => getComputedStyle(e).display === 'none').map(e => e.id || e.tagName),
                    li: getComputedStyle(document.querySelector('.toc li.brief-extra')).display,
                    strip: getComputedStyle(document.querySelector('.brief-strip')).display,
                    mode: document.documentElement.getAttribute('data-brief')};
        }""", hidden_sel)
        if printed["mode"] != "on" or printed["hidden"] or printed["total"] != total:
            fail(f"short version: print leaves sections out: {printed}")
        if printed["li"] != "list-item":
            fail(f"short version: the On this page entry prints as {printed['li']}, not a list item")
        if printed["strip"] != "none":
            fail("short version: the strip prints")
        page.emulate_media(media="screen")

        # Space on the button restores everything.
        page.focus("#brief-toggle")
        page.keyboard.press("Space")
        st = expect_state("after Space on the strip button", False)
        if st["focus"] != "brief-toggle" or st["saved"] != "off":
            fail(f"short version: restore lost focus or was not saved: {st}")
        if page.evaluate(shown_js, hidden_sel) != total:
            fail("short version: Show the full version did not bring every section back")
        page.wait_for_function("() => /Full version/.test(document.getElementById('announcer').textContent)", timeout=3000)

        # A link into a hidden section must not strand the reader: the short
        # version turns off (both controls), the section opens, and it is in view.
        def target_ok(where: str, target_id: str) -> None:
            expect_state(where, False)
            got = page.evaluate("""id => {
                const t = document.getElementById(id);
                const d = t.closest('details');
                const r = t.getBoundingClientRect();
                const bar = document.querySelector('.exit-bar').getBoundingClientRect();
                let saved = null;
                try { saved = JSON.parse(localStorage.getItem('strand:prefs')).brief; } catch (e) {}
                return {visible: t.getClientRects().length > 0, open: d ? d.open : true,
                        inView: r.top >= bar.bottom - 1 && r.top < window.innerHeight, saved: saved};
            }""", target_id)
            if got != {"visible": True, "open": True, "inView": True, "saved": "off"}:
                fail(f"short version, {where}: reader stranded at #{target_id}: {got}")

        def brief_on() -> None:
            page.evaluate("() => { if (document.documentElement.getAttribute('data-brief') !== 'on') document.getElementById('brief-toggle').click(); }")
            expect_state("turned on for a link test", True)

        brief_on()
        page.goto(base + "utah.html")
        expect_state("before following a link into a hidden section", True)
        page.goto(base + "oregon.html#q-out-of-state")      # the link the Utah page uses
        target_ok("link from another page", "q-out-of-state")
        page.wait_for_function("() => /Full version\\. The link/.test(document.getElementById('announcer').textContent)", timeout=3000)
        brief_on()
        page.evaluate("() => { window.location.hash = '#q-judge'; }")   # a link on the same page
        page.wait_for_function("() => document.documentElement.getAttribute('data-brief') === 'off'", timeout=3000)
        target_ok("link on the same page", "q-judge")
        brief_on()
        page.evaluate("""() => { const a = document.createElement('a'); a.href = '#q-judge'; a.textContent = 'x';
                                 document.querySelector('.content').appendChild(a); a.click(); }""")   # same address again: no hashchange
        target_ok("same link followed twice", "q-judge")
        brief_on()
        page.goto(base + "oregon.html#questions")           # a hidden heading
        target_ok("link to a hidden heading", "questions")
        # A link to a section that is not hidden leaves the short version on.
        brief_on()
        page.goto(base + "oregon.html#cost")
        expect_state("link to a section the short version keeps", True)
        page.evaluate("() => { window.location.hash = '#license'; }")
        expect_state("in-page link to a section the short version keeps", True)

        # "Forget everything" resets the strip too.
        page.click("#settings-open")
        page.click("#forget-all")
        page.click("#settings-close")
        expect_state("after Forget everything", False)
        if errors:
            fail(f"short version: console errors: {errors[:3]}")

        # ---- Checklist ----
        print("- checklist")
        page.goto(base + "oregon.html")
        box = page.locator('input[data-check="oregon:or-step-forms"]')
        box.check()
        if "is-done" not in (page.get_attribute("#or-step-forms", "class") or ""):
            fail("checklist: step not marked done")
        if page.evaluate("() => localStorage.getItem('strand:checks')"):
            fail("checklist: checkmarks saved without 'Remember my checklist' turned on")

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
        if p2.is_visible(".brief-strip") or p2.is_visible("#brief-toggle"):
            fail("no-js: the How much to show strip is shown even though it cannot work")
        if not p2.is_visible("#questions") or not p2.is_visible("#q-doctor"):
            fail("no-js: the full page should show, including the question sections")
        browser.close()
    httpd.shutdown()
    print(f"\n{len(problems)} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
