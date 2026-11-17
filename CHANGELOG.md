# Changelog

All notable changes to The Strand Project. Dates are when the change was published or, before launch, built.

## 0.1.11-beta (2026-11-17)

Maintenance only. No page wording, fact, or source changed, and no "checked" date moved. The only change readers can see is the version number in the footer.

- **The evidence audit now uses the same comparison rules as The Stasis Project's.** This project's first weekly audit, on November 16, 2026, was clean: 43 sources unchanged and 1 real change, a menu line on `or-ojd-forms`. The Stasis Project's was not. Its baseline had been put together from captures made by a different copy of the tool, on a different computer, and 42 of its 45 "changed" sources were artifacts of that. The same fixes are here, so a different capture computer cannot cause them in this project either.
- **Line breaks.** The hash covers the words alone, in order. Where the lines break, and characters a reader never sees, do not count. The diff compares words.
- **Replies cut short.** A reply shorter than the length it announced, or a PDF with no length and no end-of-file marker, is cut short: asked for once more and never hashed. Python's read with a size limit hands over the part that arrived without an error. One gap is known: a web page that announces no length and just stops cannot be told from a whole one.
- **Pages that are not the source.** A page that checks for automated visitors, a page with no words, and any reply with fewer than 50 words are checker-blocked, never hashed. A check page that was hashed would match itself the next week, and the source would be called unchanged although its words were never read.
- **Rules versions.** `RULES` numbers the comparison rules (now 2), and each baseline entry records the rules it was written under. An entry under other rules is "not yet baselined", never "changed". `--carry-forward` re-hashes a web page's entry from its saved text, fetching nothing. A PDF's hash is never carried forward, because its bytes are not saved and the old rules hashed a cut-short reply as if whole.
- **Refreshing a baseline.** A refresh keeps a hash it cannot replace, even one written under older rules. For each source it can read, the new entry says whether it says the same as the hash it replaces. If not, a person reads the source before the new hash is relied on.
- **The baseline.** The 29 web pages were carried forward to rules 2 from their November 15 text, with no new fetch, so the menu change on `or-ojd-forms` is still reported until a person reads it. The 15 PDFs keep their November 15 hashes under rules 1 and show as "not yet baselined" until they are written again. That run will say whether each is the same file as on November 15. 11 sources are checker-blocked and 4 unreachable, as before.
- The comparison rules are one block, the same line for line in both projects, and each project's tests check the block's hash. The tests include a fixture for each way a source looked changed, or could look unchanged, when it was not. See [docs/OPERATIONS.md](docs/OPERATIONS.md), "The comparison rules".

## 0.1.10-beta (2026-11-15)

Maintenance only. No page wording, fact, or source changed, and no "checked" date moved. The only change readers can see is the version number in the footer.

- **New: the evidence audit.** `tests/evidence_audit.py` records what each source in `data/sources.yml` says and reports when that changes. It reads robots.txt, asks one address at a time with a pause, and names itself. Web pages are compared by their readable text. PDFs are compared by their bytes, which makes a "changed" report for a PDF lower-confidence. Every source ends in one of four states: unchanged, changed, unreachable, or checker-blocked. Checker-blocked means a site refused this tool. It never means a dead link or a removed source. For a changed source, the report names the facts that cite it and the pages that show them.
- **New: the evidence baseline.** `data/evidence_baseline.yml` holds a hash of each source, written on November 15, 2026. The baselines rest on the project's November 2026 verified source checks. The run that wrote them was a tool fetching each address, not a fresh read of every source by a person. 44 of 59 sources were read (29 as text, 15 PDFs as bytes), 11 were checker-blocked, and 4 were unreachable. The 15 with no hash are listed as "not yet baselined."
- **New: the weekly source check.** `.github/workflows/weekly.yml` runs on Mondays and by hand. It runs the external link check, the freshness check, and the evidence audit, and opens one issue with all three reports when any of them needs a person. The "Checks" workflow no longer runs on a schedule or runs the link check, so each source is asked once a week, not twice.
- **New: the dated-language list.** [docs/dated-language.md](docs/dated-language.md) lists the wording whose truth depends on the date, such as "New in 2026," the 2026 fee schedules, and the passport case's "until spring 2027." Each entry says when it expires and what to do then. The first dates fall on January 1, 2027.
- **Ready, not switched on: mechanical date updates.** `tests/mechanical_update.py` can set the `checked` date for exactly the sources an audit found unchanged, and refuses any other source. It is not in any workflow. [docs/OPERATIONS.md](docs/OPERATIONS.md) says what must be settled first: the site says a person read each source on its "checked" date.
- `build.py` now lists the facts each page shows in `build-report.json`, so the audit can name the pages. The pages themselves are the same.

## 0.1.9-beta (2026-11-14)

- **Bug fix: the "Our reading" badge printed as raw markup.** The data-level badge added in 0.1.8-beta was appended to an already-escaped value in the build, so every use of the Utah $375 fact showed the badge's HTML as literal text on the page (home card, compare table, path finder, Utah page). The build now appends the badge as markup. No wording changed. `tests/check_site.py` now fails a build that contains escaped badge or link markup, so this cannot ship again.

## 0.1.8-beta (2026-11-14)

Corrections from the November 13, 2026 audit, on the maintainer's rulings of Nov. 14, 2026. The audit memo's wording is used where it proposed exact text.

- **"Sealed by the court" (Utah).** The Driver License Division's list means court papers bearing the court's seal, not sealed case files. The Utah page and the path finder now say so, with the Division's words quoted and the reading badged. The source note and research record say the same.
- **Washington enhanced licenses.** The Washington page now states the enhanced-card rule: for an EDL or EID in person, bring the filled-out form 520043 as well as your current card. Recorded in the source note and the research record; the source's checked date is now 2026-11-14.
- **Three statute-text fixes.** Utah: the guardian ad litem line now says "who is not emancipated". Washington: the comparison cell now names people required to register as a sex offender, and the fee waiver line now states the victim compensation exception. Path finder: the Utah privacy line now matches the Utah page ("Filed papers are private. The case history and public hearings are not.").
- **Two readings are now labeled.** The Oregon page's "A sex change follows the same rule" carries the "Our reading" badge while the "shall or may" question waits for a lawyer. The Utah page's name-only sentence is reworded as a reading, badged, and sourced.
- **The Utah $375 badge is now set by the data.** `ut_fee_petition` is marked as a reading in data/facts.yml, and the build adds the "Our reading" badge wherever the fact is used (home card, compare table, path finder, Utah page, quick facts). The path finder's Utah court line also carries the Utah Courts fees source marker next to the fee.
- **Federal page.** The "What still works" court orders line now reads: courts in all three states still change names; Oregon and Utah courts still order sex changes; Washington changes the marker with a form.
- **Two first-screen follow-ups from 0.1.7-beta.** The compare table's state names now link to the state pages. The after-court page's opening line now starts with certified copies, matching its step 1.
- **Records.** ORS 33.420(3)(a) is quoted in the Oregon research record and its audit flag is closed as correct. The Washington sealed-file carve-out question and the Utah name-only classification question are recorded for the states' lawyers. No page changed for either.

## 0.1.7-beta (2026-11-15)

- New "Quick facts" box near the top of the Oregon, Washington, and Utah pages, right after the big picture and the "Last checked" date. It lists, in the same order on each page: whether you need court for a name change, whether you need court for the sex or gender change, the court filing fee, the cost of certified copies, the birth certificate cost, the driver license or ID cost, the first step (a link to the steps), and anything the page flags as new in 2026.
- The box adds no new facts. Every line repeats something the same page already says, with the same source links and the same "Our reading," "Not confirmed," and "Not official" labels. The values come from `data/facts.yml` or from wording the page uses in both places, so the box and the text below it change together. No source was opened or re-checked for this release, and the "Last checked" dates did not change.
- Where a page does not give a value, the box leaves the line out. The Utah box has no license cost line, and it says the Utah birth certificate fee amounts were not found, as the page already did. The Washington box has no "new" line.
- The box stays when the short version is on, and it prints. A new browser check covers that on every state page.
- Home page: "Start here: 4 questions" and "Or go straight to your state" moved up, right after the big picture. "Why it matters" now comes after them. No words changed.
- The path finder, compare, and after-court pages were checked for the same thing (can a new reader tell what the page does and what to do first) and did not change.

## 0.1.6-beta (2026-11-14)

- Fixed a broken link. The link to the Utah Driver License Division's name change page went to a "Page not found" page. The Division moved the page. The link now goes to its current address, `https://dld.utah.gov/name-change-info/`. It appears on the Utah page (twice), the after-court checklist, the path finder, and the sources page.
- Nothing else changed. The words around the link are the same.

## 0.1.5-beta (2026-11-13)

- New strip at the top of every page, above the page title: "Still too much to take in?" with a "Show the short version" button. It turns the short version on and off without opening Reading settings. The "Short version" checkbox in Reading settings is still there, and the two always show the same choice. Nothing new is saved: the button uses the same saved reading setting.
- When the short version is on, the strip becomes a note: "You are seeing the short version. Some sections are hidden." with a "Show the full version" button. Before this, nothing on the page said that sections were hidden. Screen readers hear the change announced. The button works with Tab, Enter, and Space, keeps your place on the page, and is not shown when JavaScript is off.
- What the short version hides: the "Good questions" answers on the Oregon, Washington, and Utah pages, as before, and now their "Good questions" heading and its "On this page" entry, which used to stay behind with nothing under them. It also now hides the tips box on the after-court checklist and the "How we choose what to list" note on the help page. Steps, costs, warnings, tables, the big picture line, and "Sources for this page" always stay. On the other pages the short version changes nothing yet.
- Fixed: with the short version on, a link to a hidden section went nowhere. Now the full version comes back, the section opens, and the page goes to it.
- Printing still shows everything, and the strip does not print. New browser checks cover all of this.

## 0.1.4-beta (2026-11-03)

- Test tools only (nothing readers see changes): Playwright and axe-core versions now live in `test-tools/requirements.txt` and `test-tools/package.json`, the same versions as The Stasis Project, so Dependabot can propose updates. A new check keeps Playwright's version the same in all three places it appears.

## 0.1.3-beta (2026-11-03)

- The path finder page still lists all 24 of its sources, but the list now starts closed behind "Show all 24 sources." Each step already links its own source.
- Stricter browser security rules, now the same as The Stasis Project's: the page may load only scripts, styles, images, and the font, and only from this site.
- Code of Conduct: to report a problem, open an issue that says only that you need to report one. It no longer asks you to post a way to reach you in public.

## 0.1.2-beta (2026-11-03)

- The path finder now shows every Name step when you pick "Both": the Washington driver license step and the Utah step for a child's name change were missing for "Both." A new check tries all 180 answer combinations on every build.
- The Utah step for a child's name change now gives the steps (court, consent or service, hearing) and links to Utah Courts' page for minors. It used to link to the adult page. The Utah page's section on minors now covers name changes too.
- New public notes on how the path finder picks your steps, linked from the path finder page.
- Reading settings are now saved on your device automatically, as on The Stasis Project, so they carry from page to page. Checklist checkmarks are still saved only if you turn on "Remember my checklist." "Forget everything" erases both.
- The banner on every page now says this is an independent guide, and "Report a mistake" opens the About page first, which explains that reports and GitHub account names are public.
- Links keep one color after you visit them, as on The Stasis Project.
- License files renamed to match The Stasis Project: `LICENSE` is CC BY 4.0 for the writing, `LICENSE-CODE` is MIT for the code. The licenses did not change.
- The build no longer reads GitLab settings.

## 0.1.1-beta (2026-11-03)

- A slightly updated mark: the strand is now two twisted fibers, white and green. It now prints correctly and follows Windows high contrast themes.
- Licenses adopted: the writing is shared under CC BY 4.0 and the code under the MIT License. The About page explains how to reuse the guide and credit it.
- Build tools updated: four GitHub Actions and MarkupSafe.

## 0.1.0-beta (2026-11-03)

First beta, for private review.

- Guides for Oregon, Washington, and Utah: court steps, costs, who can see your case, birth certificates, driver licenses, minors, and help.
- Federal records page: passports and Social Security in 2026.
- 4-question path finder that shows only the steps that fit.
- After-court checklist in the right order.
- Compare table, word list, and a page listing every source with the date it was checked.
- Reading settings: text size, light, dark, and high contrast themes, extra spacing, a short version, and opt-in memory.
- Leave quickly button and Shift x3 shortcut; no cookies, tracking, or third-party code.
- Audit documentation: research memos, methodology, decision records, accessibility and privacy models, audit log, and review checklist.
- Checks in GitHub Actions: build, structure, contrast, reading level, browser, axe-core, freshness, and link checks.
- Hosting on Cloudflare Pages with clean URLs and HTTP security headers.
