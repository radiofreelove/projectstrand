# Accessibility

## Target

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) (W3C Recommendation, December 12, 2024), level AA throughout.
- Level AAA contrast (7:1) for all reading text, in every theme.
- The W3C note [Making Content Usable for People with Cognitive and Learning Disabilities](https://www.w3.org/TR/coga-usable/) (Working Group Note, April 29, 2021), which sets eight objectives. How we meet each one is below.

## How the design meets the cognitive accessibility objectives

| Objective | What the site does |
|---|---|
| 1. Help users understand what things are and how to use them | Standard underlined links, real buttons, labeled form fields, the same page structure everywhere, "Source:" and "Not confirmed" labels explained on the sources page. |
| 2. Help users find what they need | Eight-item main menu on every page, "On this page" lists, the 4-question path finder, the compare table. |
| 3. Use clear and understandable content | Smart Brevity structure, short sentences, grade 8 or lower measured on every build, a word list, legal terms defined where they appear. |
| 4. Help users avoid mistakes and know how to correct them | Fees and requirements are stated before the steps; the path finder names any unanswered question and moves focus to it. |
| 5. Help users focus | One idea per section, steps in numbered cards, "Go deeper" sections collapsed, a Short version setting that hides them. |
| 6. Ensure processes do not rely on memory | Checkable steps, print-ready checklists, copy buttons for addresses and phone numbers, an after-court checklist in order. |
| 7. Provide help and support | A help page on every menu, state help sections, a Leave quickly button, crisis and peer support at the top of the help page. |
| 8. Support adaptation and personalization | Text size, light, dark, and high contrast themes, extra letter and line spacing, an optional easy-to-read font, and respect for device settings (dark mode, more contrast, reduced motion, forced colors). |

## Key WCAG 2.2 criteria and how they are met

| Criterion | How |
|---|---|
| 1.3.1 Info and relationships | Semantic headings, lists, tables with header cells and captions, fieldsets with legends. Checked by `tests/check_site.py`. |
| 1.4.3 and 1.4.6 Contrast | Every color pair tested by `tests/contrast.py`; reading text at 7:1 or higher. |
| 1.4.10 Reflow | No sideways scrolling at 320px wide. Tables restack into cards. Checked in `tests/browser_checks.py`. |
| 1.4.11 Non-text contrast | Control borders 4.8:1 or higher; focus indicator 11:1 or higher. |
| 1.4.12 Text spacing | Tested with the WCAG spacing values injected. No overflow. |
| 2.1.1 Keyboard | Everything works by keyboard, including the settings dialog and path finder. |
| 2.4.1 Bypass blocks | "Skip to main content" link. |
| 2.4.7 and 2.4.11 Focus visible and not obscured | A gold highlight with a black underline on links; a 3px outline on controls. `scroll-padding-top` keeps focused items clear of the sticky Leave quickly bar; the browser test tabs through a long page at 1280px and 320px to confirm. |
| 2.5.8 Target size (minimum) | Controls are 44px tall or more; the test fails any control under 24 by 24px. |
| 3.1.1 Language of page | `lang="en"` on every page. |
| 3.2.3 and 3.2.4 Consistent navigation and identification | One shared layout for every page. |
| 3.3.1 and 3.3.2 Error identification, labels | The path finder lists unanswered questions by name and moves focus. |
| 4.1.2 Name, role, value | Native HTML controls and a native dialog element. |

## Contrast results (from `tests/contrast.py`, November 3, 2026)

Light theme, selected pairs:

| Text | Background | Ratio |
|---|---|---|
| Body text #414042 | Page #F4F2ED | 9.22:1 |
| Links and headings #2E3192 | Page #F4F2ED | 9.53:1 |
| Visited links #184E49 | Page #F4F2ED | 8.44:1 |
| White | Header #2E3192 | 10.66:1 |
| Body text | "Changed" callout #F3E4A1 | 8.06:1 |
| White | Leave quickly #A91F50 | 7.00:1 |
| Black | Focus highlight #ECD263 | 13.97:1 |

Dark and high contrast themes pass every pair at 7:1 or higher; the full table prints with `python3 tests/contrast.py`.

## Testing

Automated, on every push to GitHub (the fast checks also run in the Cloudflare build before each deploy):

- `tests/check_site.py`: one h1, no skipped heading levels, labeled fields, named links and buttons, valid internal links and anchors, no inline scripts or styles, `noreferrer` on outside links.
- `tests/contrast.py`: every token pair, every theme, and the device dark theme must match the manual dark theme.
- `tests/readability.py`: grade level per page and a list of sentences over 25 words.
- `tests/browser_checks.py`: Chromium at 1280px and 320px, text-spacing override, target sizes, focus visibility, the path finder, Reading settings, checklists, Leave quickly, and JavaScript turned off.
- `tests/axe_check.mjs`: axe-core on every page in all three themes. Warning-only until the first baseline is reviewed.

Manual, before each release (see [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md)):

- Keyboard only, start to finish on the path finder and one state page.
- 200% and 400% zoom.
- A screen reader pass (NVDA with Firefox or VoiceOver with Safari).
- Windows forced colors (High Contrast) mode.

## Known limits

- Not yet tested with screen reader users or with disabled and neurodivergent trans people. Paid testing is on the roadmap.
- Linked official forms are PDFs we cannot fix.
- English only.
- axe-core could not run in the environment where this beta was built (no package registry access); it runs in GitHub Actions.
