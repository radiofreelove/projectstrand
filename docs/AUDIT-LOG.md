# Audit log

A dated record of research passes, checks, decisions, and releases. Newest first. Every content change adds an entry. No personal case details.

## 2026-11-15: Evidence audit, weekly source check, and dated-language list (0.1.10-beta)

- Built to match the evidence audit in The Stasis Project. Maintenance only: no template, fact, source, or `checked` date changed. Built pages were compared with `d9b7dcf` (0.1.9-beta). The only difference is the version number in the footer.
- New `tests/evidence_audit.py`. For every source in `data/sources.yml`, it reads robots.txt, fetches the address one at a time with a pause, normalizes it (readable text for web pages, raw bytes for PDFs, since the declared test tools include no PDF library), and compares a SHA-256 with `data/evidence_baseline.yml`. States: unchanged, changed, unreachable, checker-blocked. A source with no stored hash is "not yet baselined," never "changed." For a changed source, the report names the facts that cite it and the pages that show them. `build.py` now lists each page's rendered facts in `build-report.json` for that.
- Baseline written on November 15, 2026. It rests on the project's November 2026 verified source checks. The run was a tool fetching each address, not a person re-reading each source. Results for 59 sources: 44 read (29 as text, 15 as bytes), 11 checker-blocked, 4 unreachable.
  - Checker-blocked (11): `oregonlegislature.gov` (3 sources), `pf.utleg.gov`, `legiscan.com`, `travel.state.gov` (2), and `ssa.gov` (2) answered 403 to the tool's request for robots.txt, which the tool takes as "stay out." `w3.org`'s robots.txt keeps the tool out of both WCAG sources.
  - Unreachable (4): both WashingtonLawHelp pages cut the reply short twice, `vitalrecords.health.utah.gov` failed the TLS handshake, and the ODHS brand PDF host closed the connection.
  - None of these was opened by hand for this entry. On November 14, 2026, a person opened all 8 sources the link check flags, and every one was alive. Checker-blocked and unreachable are about the tool, not the sources.
- The first compare run, minutes after the baseline, called 2 sources changed whose words had not changed. `wa-courts-forms` prints its serving node ("N1," "N2"). `us-lambda-helpdesk`'s contact form gives a hidden spam-trap field a random label. Both lines are now dropped before hashing (the `VOLATILE` list in the tool), and both sources were re-baselined. Two more compare runs: 44 unchanged, 0 changed.
- New `.github/workflows/weekly.yml`: Mondays and by hand, the link check, `freshness.py`, and the evidence audit, with one issue when any needs a person. Permissions: contents read, issues write. The "Checks" workflow's schedule trigger and external-links job were removed so each source is asked once a week. The link check still flags the sites that refuse scripts, so expect the weekly issue to open until those are handled.
- New `tests/mechanical_update.py`, draft-only and not in any workflow. It may move `checked` dates only for sources an audit found unchanged. A dry run against the November 15 audit would have moved 44 dates. It was not run for real. `docs/OPERATIONS.md` records the question to settle before turning it on: the site says a person read each source on its "checked" date.
- New `docs/dated-language.md`: 11 items to act on (8 with dates, 3 waiting on someone else's next step), and the dated wording that stays true. The first dates fall on January 1, 2027. `freshness.py` and `data/site.yml` have no checkpoint mechanism, so the file is the register.
- Checks after the change, run on November 15, 2026: build (16 pages, 59 sources, 36 facts, no warnings), `check_site.py` in both link styles (16 of 16), `contrast.py` (0 problems), `readability.py` (highest grade 5.0), `path_rules.py` (180 combinations), `check_versions.py`, `freshness.py`, `tools/release_notes.py --check`, `browser_checks.py` (0 problems), `test_evidence_audit.py` (34 tests), and `test_mechanical_update.py` (10 tests) all pass. `axe_check.mjs` was not run; no page markup changed.
- The old-name sweep of the changes: cleared.

## 2026-11-14: Badge escaping bug fixed (0.1.9-beta)

- The maintainer spotted raw badge markup printed as text on the home page Utah card, live from 0.1.8-beta. Root cause: in `build.py`, `fact()` appended the badge string to a markupsafe-escaped value with `+=`, which escapes the appended string. Every rendered use of `ut_fee_petition` was affected (index, compare, path, and four places on the Utah page, including the quick facts strip).
- Fix: append the badge as a `Markup` object. Added a guard to `tests/check_site.py`: a built page containing `&lt;span` or `&lt;a ` fails the check. Verified the guard fails on the 0.1.8-beta output and passes on the fixed build.

## 2026-11-14: Audit corrections applied (0.1.8-beta)

- The maintainer ruled on the November 13, 2026 audit flags on November 14, 2026: the Utah driver license address stands as fixed in 0.1.6-beta; the memo's exact corrections for "sealed by the court" were adopted; the Washington enhanced license sentence was added as proposed; the fix-now batch (UT-3a, WA-3a, WA-3b, UT-3c) was applied; OR-3 was confirmed correct and closed with the ORS 33.420(3)(a) quote added to the Oregon research record; OR-2 and UT-3b were labeled "Our reading" as interim fixes; WA-3c and the X-3 lawyer question were recorded, with X-3's rewording applied to the federal page; and the Utah $375 badge was fixed at the data level (X-2).
- Build change: `build.py`'s fact helper appends the "Our reading" badge when a fact carries `reading: true` in `data/facts.yml`. Only `ut_fee_petition` carries it. The two hand-placed badges on the Utah page were removed so no page shows it twice.
- Also applied, from the 0.1.7-beta first-screen audit's open notes, on the maintainer's direction: the compare table's state names link to the state pages, and the after-court opening line starts with certified copies, matching its step 1.
- The old-name sweep of the changes: cleared.

## 2026-11-15: "Quick facts" strip on the state pages (0.1.7-beta)

- Approved by the maintainer on November 13, 2026. Built on November 14 and 15, 2026. This is a layout change. No source was opened or re-checked for it, and no `checked` date changed.
- New macro `m.quickfacts()` in `templates/macros.html.j2`, called on the Oregon, Washington, and Utah pages right after the checked line. It is a callout and is never marked as an extra, so Short version mode keeps it and it prints.
- Every value in the strip restates what the same page already says with a source. 11 facts were added to `data/facts.yml` for wording that used to be typed into a page (25 facts before, 36 now): `or_court_name`, `or_court_sex`, `or_dmv_fee`, `wa_court_name`, `wa_court_marker`, `wa_doh_amend_fee`, `wa_dol_fee`, `ut_court_name`, `ut_court_sex`, `ut_vital_amend_fee`, `ut_hb183_status`. Each one's note names the page statement it restates and cites that statement's sources. Where the page text could pull the new fact without changing its words, it now does. Compared the built pages with `main` (`581e06c`): outside the strip, the words on the three state pages are the same. Their "Sources for this page" lists hold the same sources in a new order, because the build lists sources in the order a page first uses them.
- Two strip lines are typed in a page template and not shared with the text below: Oregon's "New in 2026" line (it joins the title and first sentence of the page's "New in 2026" box; the date is a fact) and Washington's filing fee line (it restates "Fees vary by court" in step 3 and the sealed line of "What it costs"; the amount is a fact). A comment in each template says so.
- Left out where the page gives no value: Utah has no license or ID cost row. Washington has no "new" row. Utah's birth certificate row keeps "We could not find the amounts" and its "Not confirmed" label, and Utah's filing fee keeps "Our reading."
- First-screen check of four shared pages (can a new reader tell what the page does and what to do first), at 1280 by 800 and 390 by 760 in Chromium:
  - Home: the page said what it does, but "Start here" sat below the "Why it matters" numbers. Moved "Start here" and "Or go straight to your state" up to follow the big picture. No words changed.
  - Path finder: passes. The big picture says "Answer 4 questions" and question 1 follows it. No change.
  - Compare: passes. The big picture says what the table shows, and the table follows it. No change. Noted: the table's state names do not link to the state pages.
  - After court: passes. The big picture names the order and says the page is a checklist. No change. Noted: the big picture says "Start with Social Security," and step 1 is "Get certified copies of your court order."
  - Open, for the maintainer: the shared header, menu, banner, and "Still too much to take in?" strip fill about 540px at 1280px wide and more than one whole screen at 390px wide. On a phone, no page's own heading is on the first screen. The header's mission lines and the "Start here" menu item are. Not changed here.
- `tests/browser_checks.py` has a new "quick facts" section for each state page: one strip, right after the checked line and before any other callout, every row filled in, its links resolve, its first step matches the page's step 1, and it is fully shown in Short version mode and in print. Confirmed it fails when a built page is broken on purpose.
- Looked at the strip in Chromium at 1280px and 320px, in the light, dark, and high contrast themes, in print, and with forced colors emulated. It uses the surface, text, heading, link, and badge colors that `tests/contrast.py` already checks.
- Checks after the change, run on November 15, 2026: build (16 pages, 59 sources, 36 facts, no warnings), `check_site.py` in both link styles (16 of 16), `contrast.py` (0 problems), `readability.py` (highest grade 5.0; the same 5 long sentences as before, none in the strip), `path_rules.py` (180 combinations), `check_versions.py`, `browser_checks.py` (0 problems), `freshness.py`, and `axe_check.mjs` (0 serious or critical, 48 page and theme runs) all pass. `check_external_links.py`, the scheduled warning-only check, listed 8 links for a person to open (6 answered 403 to the script and 2 did not connect). This change touched no link, and none of the 8 was opened by hand here.

## 2026-11-14: Utah driver license link fixed (0.1.6-beta)

- The November 13 link check found one dead link: source `ut-dld-name`, `https://dld.utah.gov/name-change/`, returned 404. It showed in five places: the Utah page (twice), the after-court checklist, the path finder, and the sources page.
- Opened on November 14, 2026, all on the Division's own site: the old address still returns "Page not found." The Division's Required Documents page says "View the list of acceptable documents if your name has changed" and links to `https://dld.utah.gov/name-change-sort/`. The Division's server redirects that address, permanently, to `https://dld.utah.gov/name-change-info/`, and the page names that same address as its own. Its title is "Name Change Information."
- Read the page in full. It says a name change needs an office visit and "legal documentation," and it lists the documents the Division accepts. It says nothing about sex designation. That matches what the site says around the link.
- Change: `url` in `data/sources.yml` is now `https://dld.utah.gov/name-change-info/`, the address the redirect ends at, and `checked` is 2026-11-14. The link in `docs/research/utah.md` and its research log are updated. No template, fact, title, or wording changed.
- Open, not changed here: the page lists "Court papers showing the name change, sealed by the court." The site says the Division "accepts sealed court documents." Whether that wording should change is with the maintainer.
- Checks after the change: build (16 pages, 59 sources, 25 facts), `check_site.py` in both link styles (16 of 16), `contrast.py` (0 problems), `readability.py` (highest grade 5.0), `path_rules.py` (180 combinations), `check_versions.py`, `browser_checks.py` (0 problems), `freshness.py`, and `axe_check.mjs` (0 serious or critical) all pass.

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
