# Changelog

All notable changes to The Strand Project. Dates are when the change was published or, before launch, built.

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
