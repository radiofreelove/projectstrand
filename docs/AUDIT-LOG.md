# Audit log

A dated record of research passes, checks, decisions, and releases. Newest first. Every content change adds an entry. No personal case details.

## 2026-11-03 (night): first Dependabot updates for the test tools

- Waited for the Cloudflare deploy of `6e82cea` (the Dependabot fix) to finish before merging anything, so each change could be traced.
- Merged #6: axe-core 4.10.2 to 4.14.0 in `test-tools/package.json`. All checks had passed on the pull request.
- Playwright 1.63.0 to 1.64.1 in one commit (`test-tools/requirements.txt`, `test-tools/package.json`, and the axe job's container `mcr.microsoft.com/playwright:v1.64.1-noble`, which Playwright's Docker page lists). This replaces Dependabot's #7, #8, and #9, which could each change only one place and so failed `tests/check_versions.py`. Closed #8 as a duplicate of #7. `docs/OPERATIONS.md` now says Playwright updates are always one three-place commit.
- Stasis merged the same versions the same day. ADR-0010 no longer names version numbers; they live only in `test-tools/`.

## 2026-11-03 (night): third review follow-up (0.1.4-beta)

- A third review grepped both trees for residue (old project names, TODO and FIXME markers, old repository links, GitLab leftovers outside history) and found none. Confirmed.
- Test tool versions: Playwright 1.63.0 and axe-core 4.10.2 were written inside workflow commands, where Dependabot cannot see them. They now live in `test-tools/requirements.txt` and `test-tools/package.json`, and Dependabot watches npm as well as pip and GitHub Actions. Stasis uses the same files and versions. Both files sit in `test-tools/`, not the root: Cloudflare Pages installs a root `package.json` on every deploy (Cloudflare build image docs, updated Oct. 26, 2026). The axe job links `test-tools/node_modules` to `node_modules` so `tests/axe_check.mjs` can import them.
- Dependabot does not update the axe job's container tag (`mcr.microsoft.com/playwright:v1.63.0-noble`), which must match Playwright's version, and that job is warning-only, so a mismatch could quietly stop axe-core from running. New `tests/check_versions.py` fails the build job until all three match. Confirmed it fails on a mismatch and passes now.
- Dependabot ran right after the push and opened npm proposals from `test-tools/package.json` without a lockfile, so that works. Its root pip entry also read `test-tools/requirements.txt`, so a separate pip entry for `/test-tools` opened a duplicate Playwright proposal (#7 and #8). The extra entry is removed. Playwright proposals (#7 or #8, and #9) fail `tests/check_versions.py` one at a time by design; Playwright moves only when both files and the container tag change together.

## 2026-11-03 (night): second review follow-up (0.1.3-beta)

- A second outside review compared live headers and both repository roots. Each claim was checked against both repositories first.
- Path finder sources: the page lists 24 sources (the review's count). They now sit in a closed "Show all 24 sources" toggle, set by `tool: true` in `data/pages.yml`. Every source is still listed, so the build rule holds. The toggle does not use the `.deeper` class, so "Short version" never hides it.
- Headers: the Content Security Policy now matches Stasis: `default-src 'none'` and `base-uri 'none'` (were `'self'`), no `data:` images (none were used), and no `upgrade-insecure-requests` (every resource is same-site). The meta tag in `templates/base.html.j2` and `site-root/_headers` both changed. `tests/check_site.py` now fails if either differs from the shared header set in ADR-0010. Checked in Chromium: no policy violations on any page.
- Code of Conduct: the reporting step asked people to post "how to reach you" in a public issue, which contradicted its own "Do not post details publicly." It now asks for an issue that says only that a report is needed; a maintainer replies with a private channel. Stasis now has the same code, adapted for its readers.
- ADR-0010 records the shared headers, tool-page source lists, code of conduct, and the different doc naming (kept on purpose).

## 2026-11-03 (evening): review follow-up and shared conventions with Stasis (0.1.2-beta)

- An outside review compared this project with The Stasis Project. Each claim was checked against both repositories before acting on it. Shared conventions are now recorded in ADR-0010.
- Path finder: two "Both" gaps fixed. With "Both" selected, the Washington Department of Licensing name step (`t-id-wa`) and the Utah step for a child's name change (`t-court-ut`) were hidden, because their lines were marked for "Name" only. Both now show for "Name" and "Both." Found by trying every combination of questions 2 and 3 against every result block; `tests/path_rules.py` now runs that check (180 answer combinations) in GitHub Actions and in the Cloudflare build. The test fails on the old template and passes on the new one.
- Utah, child's name change: the path finder line pointed to the Utah Courts adult page (`ut-courts-sex-change`). Read Utah Courts' page for minors ("Name or Sex Designation Change - Minor") and registered it as `ut-courts-minor-change`. The line now says: file in the district court in the county where the child has lived for the past year; the other parent signs a consent form or is served; there is a hearing. Added the same paragraph to the Utah page's minors section. The page does not say who files or whether name-only cases for minors are public, so the site does not say either. Research memo updated.
- Reading settings: saved automatically at the maintainer's request, matching Stasis (ADR-0002 updated, ADR-0010). Checkmarks still need "Remember my checklist." The privacy page now says a saved-settings entry shows the site was used, much like history. `tests/browser_checks.py` checks that settings carry over, that checkmarks are not saved without Remember, and that "Forget everything" erases every `strand:` key.
- New `docs/PATH-LOGIC.md`: every question, the block order, and which lines each answer shows, in plain words, matching Stasis's `checker-logic.md`. Linked from the path finder page and the README.
- Banner: "Independent guide. Not run by any court or government agency." now leads the beta banner, as on Stasis. "Report a mistake" now opens About, `#report`, which says the report and the GitHub account name are public, then links to the issue tracker. The About page's beta notice links there too. `docs/PRIVACY.md` adds the account-name risk. A reporting form that needs no GitHub account would need server code, which ADR-0001 (a static site) rules out; the maintainer chose to keep GitHub issues as the only route.
- Links: visited links no longer turn green. `--link-visited` and its contrast pairs are removed; Stasis uses one link color.
- Licenses: `LICENSE` (MIT) renamed to `LICENSE-CODE`, and `LICENSE-CONTENT` (CC BY 4.0) renamed to `LICENSE`, matching Stasis. Texts unchanged. README, REUSING, and CONTRIBUTING links updated; ADR-0008 notes the rename.
- Build: removed the GitLab fallbacks (`CI_PAGES_URL`, `CI_PROJECT_URL`, `CI_COMMIT_SHA`, and GitLab-style issue links) from `build.py` and the comment in `data/site.yml`. GitLab mentions in earlier ADRs and log entries stay as history.

## 2026-11-03 (later): updates merged, new mark, licenses adopted (0.1.1-beta)

- Merged Dependabot's five update proposals after reading their release notes: actions/checkout 4 to 7 (#2), actions/setup-python 5 to 7 (#4), actions/upload-artifact 4 to 7 (#3), actions/download-artifact 4 to 8 (#5), and MarkupSafe 3.0.3 to 3.0.4 (#1). The breaking changes they list (Node 24 runners, new checkout rules for `pull_request_target`, digest checks on download) do not affect this workflow. Each new version had already run cleanly on its own pull request. The failed checks there came from the pull requests' older starting commit, before the browser and axe fixes.
- #2 changes lines next to the ones #4 and #5 change, so it went last: Dependabot rebased it, and its checks passed on all five changes together. On `main` at `1b8f989`, build and fast checks, browser checks, axe-core, and the Cloudflare deploy passed. Runs for two in-between commits were cancelled by the workflow's concurrency rule, as designed.
- New mark (ADR-0009): two twisted fibers, white and willamette green, drawn by `scripts/make_mark.py`. `tests/contrast.py` now also checks the mark's colors and the current-page underline against each header background. Green: 5.26:1 on the light theme's indigo, 9.25:1 on the dark theme's header, 10.37:1 on high contrast black. Gold: 7.09:1 or more.
- Fixed: the mark disappeared in print (white on white) and in light Windows high contrast themes. Checked by screenshot in the light, dark, and high contrast themes, in print, and with forced colors emulated in Chromium (dark and light).
- Licenses adopted (ADR-0008). `LICENSE` is now the plain MIT text; GitHub had labeled it "Other" because of a note added at the end. `LICENSE-CONTENT` holds the full CC BY 4.0 legal code. New: `docs/REUSING.md`, a licensing section in `CONTRIBUTING.md`, the license line in every footer, and "Reuse this guide" on the About page.

## 2026-11-03 (later): re-trigger after a silent push

- Commit `962fb69` (font pin and table links) built and deployed on Cloudflare Pages; Cloudflare reported "Deployed successfully" on GitHub.
- Commit `540366f` (Copy button rows) reached GitHub's `main`, but the push returned a "cannot lock ref" error and no GitHub Actions run or Cloudflare build started for it. This commit exists to trigger both. Future pushes from this environment turn off Git's push negotiation, which was printing warnings on every push here (inference: the warnings and the missing run are related).

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
9. Maintainer decisions: independence check on the palette (ADR-0003) and repository visibility. Done: licenses (ADR-0008).
