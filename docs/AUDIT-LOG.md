# Audit log

A dated record of research passes, checks, decisions, and releases. Newest first. Every content change adds an entry. No personal case details.

## 2026-11-03 (later): third check run, Copy button fix

- Third GitHub Actions run: build, fast checks, and browser checks passed. The pinned font files matched their checksums. axe-core, now naming the element, flagged the Copy button for the Oregon State Bar phone numbers: a source link right after it wrapped onto the next line, and that link's bounding box covered the button.
- The earlier table-link change did not cause or fix this finding (inference: the table links were not the flagged element).
- Fix: every Copy button now sits on its own row with its number, address, or email, after the sentence instead of inside it. Long emails can wrap so the row never forces sideways scrolling.
- Added an overlap check to `tests/browser_checks.py` that mimics how axe-core measures covered targets. Run against the pushed version, it reproduced axe's finding on the Oregon page, plus the same pattern on the Washington page at phone width. After the fix it finds nothing at 1280px or 320px.

## 2026-11-03 (later): first deployment to Cloudflare Pages

- The maintainer connected the repository to Cloudflare Pages. The live site at `https://projectstrand.pages.dev` was built from commit `da56867`, with clean URLs and the optional font bundled. Its build report lists no warnings.
- Second GitHub Actions run: build, fast checks, and browser checks passed. axe-core found no landmark problems and one remaining target-size finding on the Oregon page (one element, in each theme). The axe script did not print which element, so it now does.
- Likely cause (inference): links that sit alone in the "Where to go" column of the Oregon table wrap into several line fragments. Those links are now single boxes with taller padding.
- Pinned the font: version 5.3.0 of the Fontsource package, with SHA-256 values recorded from the first build with network access. A changed file now fails the build.
- Dependabot opened five update proposals (four GitHub Actions and MarkupSafe). They are left for the maintainer to review.

## 2026-11-03 (later): first GitHub Actions run and fixes

- First run of the "Checks" workflow on GitHub: build and fast checks passed. The browser job failed before running any test, because the Playwright Python package was not installed in the job's container. axe-core ran for the first time and reported 3 serious findings (one link target under 24px with crowded neighbors on the Oregon page, in each of the 3 themes) and 48 moderate findings (2 page elements outside landmarks on all 16 pages, in each theme).
- Fixes: the Leave quickly bar is now a labeled navigation landmark; the beta notice and the status announcer moved inside the main landmark; links in the content get vertical padding so every link target is at least 24px tall; the browser job now installs Playwright and Chromium on a standard runner.
- Local checks after the fixes: an approximation of axe's landmark and target-size rules finds 0 issues on all 16 pages at 1280px and 390px; structure, contrast, and browser checks pass in both link styles. axe-core itself reruns on the next push.

## 2026-11-03 (later): moved to GitHub and Cloudflare Pages

- The GitLab project was renamed twice and then deleted by the maintainer before anything was pushed. No content ever lived on GitLab.
- New home for the code and audit trail: `github.com/radiofreelove/projectstrand`. New host for the site: Cloudflare Pages, project `projectstrand`, intended address `https://projectstrand.pages.dev` (ADR-0004).
- Replaced the GitLab pipeline with a GitHub Actions workflow (`.github/workflows/checks.yml`) running the same checks, plus a weekly freshness and link report. Added Dependabot for monthly update proposals.
- Moved issue and merge request templates to GitHub issue and pull request templates. Turned off blank issues so every report starts with the privacy reminder.
- Added `scripts/cloudflare_build.sh` (build command for Cloudflare Pages, runs the fast checks before deploying), `.python-version` (3.13), and `site-root/_headers` (Content Security Policy with `frame-ancestors 'none'`, HSTS, `nosniff`, `X-Frame-Options`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`, `Permissions-Policy`).
- Added clean URLs for Cloudflare builds, because Cloudflare redirects `.html` addresses to extensionless ones; `tests/check_site.py` now validates both link styles.
- Updated the privacy page and privacy model to name Cloudflare as the host and keep Cloudflare Web Analytics off.
- Checks after the move: both link styles pass `tests/check_site.py` (16 of 16 pages); contrast, reading level, and browser checks unchanged and passing.

## 2026-11-03: version 0.1.0-beta built

### Research pass

- Opened and read 58 sources: 30 official and verified, 5 secondary (legal aid, advocacy, a bill tracker), 21 linked forms and directories, and 2 that could not be confirmed. 4 are used only in the research memos. Full list: `data/sources.yml`. Details: `docs/research/`.
- Currency checks: Oregon session laws for 2026 (chapters 52 and 88); Washington 2025 sections affected; Utah code PDFs current through the 2026 session and the status of 2026 H.B. 183; federal policy updates through the ACLU's October 2, 2026 case update.
- Blocked or unavailable: Oregon 2026 amendments and repeals table (bot detection), Oregon DOJ Address Confidentiality Program page, the Washington RCW web page (robots rules; used the certified PDF), Utah bill and code HTML pages (JavaScript only; used PDFs), U.S. State Department sex marker pages, and the font CDN and package registries from the build environment.

### What the beta contains

- 16 pages: home, path finder, Oregon, Washington, Utah, federal records, after-court checklist, help, compare, why this exists, word list, sources, about, accessibility, privacy, and a 404 page.
- 25 facts in `data/facts.yml`, each tied to its sources.

### Checks run on the built site

| Check | Result |
|---|---|
| `tests/check_site.py` (structure, links, labels, CSP safety) | 16 of 16 pages pass |
| `tests/contrast.py` (light, dark, high contrast) | 0 problems; reading text 7:1 or higher in every theme |
| `tests/readability.py` | Highest estimated grade 5.2; 3 sentences over 25 words remain, all quotes or source notes |
| `tests/browser_checks.py` (Chromium) | 0 problems: no errors or CSP violations, reflow at 320px, text spacing, target size, focus visible and not obscured, path finder, settings, checklists, Leave quickly, JavaScript off |
| `tests/freshness.py` | All sources checked within 120 days |
| `tests/axe_check.mjs` | Not run in the build environment (no package registry access). Runs in GitHub Actions as a warning-only job. |

### Fixes made during checking

- Source labels could not wrap and pushed pages sideways at 320px. Allowed wrapping.
- Dark-mode visited links measured 6.2 to 6.8:1 on tinted callouts. Changed to a lighter green (7.8:1 or higher).
- Home page cards were wider than a 320px screen. Set a responsive minimum.
- Added scroll padding so focused items never sit under the sticky Leave quickly bar.
- Shortened 25 sentences that ran over 25 words.

### Repository

- Prepared for GitLab at first; see the later entry above for the move to GitHub and Cloudflare Pages.

### Open items

1. Legal review by a lawyer licensed in each state (required before 1.0).
2. Paid usability testing with trans, nonbinary, disabled, and neurodivergent people.
3. Done: font version and hashes pinned (see the entry above).
4. Review the first axe-core results and make the axe job blocking.
5. Ask Oregon Vital Records how footnotes work after a confidential 2026 case.
6. Confirm Utah Driver License Division's sex designation process and Utah Vital Records fees.
7. Confirm the U.S. State Department's current sex marker page text.
8. Check Washington's 2026 sections-affected table when published.
9. Maintainer decisions: content and code licenses; independence check on the palette (ADR-0003); repository visibility.
