# Dated language

Words on the site whose truth depends on the date. Some will read as wrong once a date passes. Others stay true but describe a version of a law, fee schedule, or form that a newer one can replace.

Swept on November 15, 2026, from the files the build turns into pages: `templates/` (every page and the shared macros), `data/facts.yml`, and `data/pages.yml`. A short last section covers version labels in `data/sources.yml` that the sources page and each page's source list show. Nothing on the site was changed by this sweep.

## This file is the register

`tests/freshness.py` and `data/site.yml` have no checkpoint or watch list. They track one thing: how old each `checked` date is (120 days). Nothing there fits a date set in advance, so this file is where the dated items are registered. Nothing here runs by itself, and no scheduled check reads this file. Here is what keeps it from being forgotten:

- **Look at this file at the start of each month,** and again whenever the weekly source check opens an issue.
- **When you change a page,** search this file for the template or fact you touched. If an entry quotes wording you changed, update the entry or close it.
- **When a date passes,** do what the entry's "When the date passes" line says. Then move the entry to "Closed" with the date and what you did. Log it in [AUDIT-LOG.md](AUDIT-LOG.md).
- **When you add dated wording,** add an entry here in the same change.

The evidence audit (`tests/evidence_audit.py`) helps with the "Upstream" items below, because it reports when a source's content changes. It cannot tell that a calendar date passed. Several of the sources these items rest on are checker-blocked for that tool, so a person must open them anyway (see each entry).

Wording changes go through the usual review. Each "When the date passes" line names the question to settle. It is not pre-approved new wording.

## Expires on a date

### DL-01. "New in 2026" (Oregon confidential cases)

- **Wording:** "New in 2026: sex change cases are confidential" (callout title) and "New in 2026" (the Quick facts row label).
- **Where:** `templates/pages/oregon.html.j2`, the callout with id `or-confidential` and the `whats_new` label passed to `m.quickfacts()`. Shown on the Oregon page.
- **Expires:** January 1, 2027. The rule is still in force after that, but in 2027 it is not new.
- **When the date passes:** retitle both so they do not say "new," keeping the date the rule began (`or_confidential_date`, July 1, 2026). Ask whether the Quick facts strip should still have a "new" row for Oregon. If it should not, remove it, the way the Washington strip has none. Update the comment above `confidential` in the template to match.

### DL-02. "Changed in 2026" badge

- **Wording:** "Changed in 2026".
- **Where:** `templates/macros.html.j2`, `m.badge('changed')`. Used once: next to the Oregon page heading "Who can see your case."
- **Expires:** January 1, 2027.
- **When the date passes:** decide whether the badge should come off that heading. If the project wants a "changed" badge in 2027, the year has to change, or the badge has to name the date instead of the year. The year is written into the macro, so any page that uses the badge picks it up.

### DL-03. "What changed in 2026" (home page)

- **Wording:** the callout title "What changed in 2026", and its three lines. The Oregon line starts "since July 1, 2026, court cases for a legal change of sex…". The Utah line says H.B. 183 "stalled in a Senate committee and is listed as not passed". The Federal line ends "The court case continues into 2027."
- **Where:** `templates/pages/index.html.j2`, the callout with id `changed-2026`. Shown on the home page.
- **Expires:** January 1, 2027. The box reads as last year's news after that. The Federal line's end date is also in DL-07, and the Utah line's in DL-05.
- **When the date passes:** decide what the box becomes: "What changed in 2026" kept as history, a new box for 2027, or no box. Check the Federal and Utah lines against DL-05 and DL-07 at the same time.

### DL-04. "Passports and Social Security in 2026" (federal page title)

- **Wording:** "Passports and Social Security in 2026" (page title, heading, and browser tab). Description: "What changed for passports and Social Security records in 2025 and 2026, and what to know before you apply."
- **Where:** `data/pages.yml` (`federal`: `title`, `description`), `templates/pages/federal.html.j2` (the `h1`), and the link text "Passports and Social Security in 2026" in `templates/pages/compare.html.j2` and `templates/pages/path.html.j2`. The page's file name and address do not carry the year.
- **Expires:** January 1, 2027. Search results and the page title would read as last year's page.
- **When the date passes:** re-check the federal page against its sources first (DL-07, DL-10). Then decide the title. Change `data/pages.yml`, the `h1`, and both link texts together.

### DL-05. Utah H.B. 183, "What happened in 2026"

- **Wording:** callout title "What happened in 2026". Text: "A 2026 bill called H.B. 183, "Sex Designation Amendments," would have changed these rules. A Senate committee sent it back to the Rules Committee on March 4, 2026, and a bill tracker lists it as not passed." The fact `ut_hb183_status`: "H.B. 183, a 2026 bill that would have changed these rules, is listed as not passed". Quick facts row label "What happened in 2026", with the link "More about the 2026 bill".
- **Where:** `templates/pages/utah.html.j2` (callout `ut-2026` and the `whats_new` row), `data/facts.yml` (`ut_hb183_status`). Also the home page Utah line in DL-03.
- **Expires:** when Utah's 2027 General Session opens in late January 2027 (the Utah Constitution sets the fourth Monday of January). From then on, a new bill could change these rules, and "the 2026 bill" stops being the latest news. Check again when the session ends in early March 2027.
- **When the date passes:** search the Utah Legislature's site for 2027 bills on sex designation or name changes. If there is one, the box and the Quick facts row need a decision. If there is none, decide whether the 2026 box still earns its place. Both sources are checker-blocked for the evidence audit (`ut-hb183-notice`, `ut-hb183-legiscan`), so a person opens them.

### DL-06. Oregon court fees, from the 2026 fee schedule

- **Wording:** `or_fee_petition` "$124", `or_fee_certified_copy` "$5 per certified copy, plus 25 cents a page for paper copies", `or_fee_waiver_application` "no fee to apply". Used on the home, path finder, Oregon, compare, and after-court pages, and in the Oregon page description in `data/pages.yml` ("the $124 fee").
- **Where:** `data/facts.yml`, source `or-ojd-fees`, "Circuit Court Fee Schedule, effective January 1, 2026".
- **Expires:** January 1, 2027, the first date a new yearly schedule could take effect. Fee laws passed in Oregon's 2027 session could also change fees later in 2027.
- **When the date passes:** open the Oregon Judicial Department's fee schedule page and look for a schedule dated 2027. If there is one, follow "Update a fee or other fact" in [OPERATIONS.md](OPERATIONS.md). Its address will be new, so the source's `url` changes and its evidence baseline starts over. The `data/pages.yml` description is typed text, not a fact, so change it by hand. The evidence audit watches the 2026 schedule PDF by its bytes, but a new schedule at a new address would not show up as a change.

### DL-07. Orr v. Trump: "As of September 2026" and "until spring 2027"

- **Wording:** "As of September 2026, the case is back in the trial court and in "discovery," the stage where each side gathers information. The ACLU expects that to last at least until spring 2027." Also, on the home page: "The court case continues into 2027."
- **Where:** `templates/pages/federal.html.j2` (section "The court case"), `templates/pages/index.html.j2` (DL-03).
- **Expires:** spring 2027. Treat March 20, 2027 as the check date. "As of September 2026" gets older every month, and any ruling before then changes the page.
- **When the date passes:** open the ACLU case page (`us-aclu-orr`) and the Human Rights Campaign page (`us-hrc-passport`). Update the status line and its "as of" date, or confirm it and record the check. The evidence audit can read both pages, so a "changed" report for either is the earlier signal to do this.

### DL-08. Utah court fees, effective May 6, 2026

- **Wording:** `ut_fee_petition` "$375" (badged "Our reading"), `ut_fee_cert_copy` "$4 per document plus 50 cents per page". Used on the home, path finder, Utah, compare, and after-court pages, and in the Utah page description in `data/pages.yml` ("the $375 fee").
- **Where:** `data/facts.yml`, source `ut-courts-fees` ("Fees effective May 6, 2026").
- **Expires:** early May 2027. Utah fee changes passed in a general session usually take effect in May.
- **When the date passes:** open the Utah Courts fees page and compare the general civil filing fee and the copy fees. Follow "Update a fee or other fact" if they changed. The evidence audit reads this page as text, so a fee change there should show as "changed" before this date. Still open the page on this date, because the page could change somewhere the audit cannot see.

## Upstream: true until a law, form, or office changes

These have no date when they stop being true. They depend on someone else's next step. Re-check them when the source is re-checked, when the evidence audit reports their source as changed, or by the date given.

### DL-09. "Right now" at Social Security and the State Department

- **Wording:** "Right now these offices do not change sex markers, even with a court order." (Oregon page, "Do you need court?" table). "Social Security is not changing sex markers right now." (after-court checklist, path finder). Also, on the federal page: "Social Security stopped changing sex markers."
- **Where:** `templates/pages/oregon.html.j2`, `templates/pages/after.html.j2`, `templates/pages/path.html.j2`, `templates/pages/federal.html.j2`.
- **Expires:** when federal policy changes. No date is set.
- **When to check:** with DL-07, and at each re-check of `or-dmv-gender` and `us-hrc-passport`. The Social Security pages (`us-ssa-name`, `us-ssa-sex-redirect`) and the State Department pages are checker-blocked for the evidence audit, so a person opens them.

### DL-10. Passports issued before the change

- **Wording:** "Search results quoted the State Department as saying passports issued before the change stay valid until they expire. We could not open the department's page to confirm it."
- **Where:** `templates/pages/federal.html.j2`. Source `us-state-sex-marker`, status unverified.
- **Expires:** when the State Department page says otherwise, or when someone opens it and confirms it.
- **When to check:** with DL-07. The page is checker-blocked for the evidence audit, so a person opens it.

### DL-11. Oregon statute edition

- **Wording:** "ORS chapter 33 (2025 edition): sections 33.410, 33.420, 33.460" (source title, on the sources page and in the Oregon page's source list). The notes say to read it with 2026 Oregon Laws chapters 52 and 88.
- **Where:** `data/sources.yml`, `or-ors-33`.
- **Expires:** when the Legislature publishes the 2027 edition of the ORS, after the 2027 session.
- **When to check:** at the next Oregon re-check after the 2027 session ends. Confirm the 2026 amendments are in the new edition, then update the source. The Legislature's site is checker-blocked for the evidence audit (its robots.txt refuses this tool), so a person opens it.

## Dated, and stays true

These name a past date. They do not go wrong when time passes, so they have no action. They are listed so the next sweep does not have to look at them again.

- "Since July 1, 2026, any case that includes a sex change is confidential by law." (Oregon page lede.) "For cases filed on or after July 1, 2026…", "Filed before July 1, 2026?", and "I filed before July 1, 2026. Is my old case public?" (Oregon page). These use `or_confidential_date`.
- "Two federal offices changed course in 2025." (federal lede.) "Both changed in 2025." (home page card.) "On January 20, 2025, an executive order changed the rules." "A federal court blocked the policy in June 2025. In November 2025, the U.S. Supreme Court let the government enforce it while the case continues." "as of January 31, 2025, Social Security was directed to stop processing gender marker updates."
- "The law on this page is the version that took effect May 7, 2025." (Utah page.)
- "Oregon made sex change cases confidential in 2026. Federal passport and Social Security rules changed in 2025. A guide from two years ago can send you the wrong way." (why page.) "Two years ago" is relative to the reader's own day. It stays a fair warning.
- The 2022 U.S. Trans Survey figures and dates (home and why pages). They describe one survey.
- "How the three states compare, as of" the page's checked date (compare page caption), and every "Checked" or "Last checked" line. The build fills these in from `data/pages.yml` and `data/sources.yml`.

## Version labels in data/sources.yml

The sources page and each page's source list show each source's `date` field, such as "Forms dated July 2026" (Oregon adult packet), "Live page; form OHA 2673 rev. 03/26" (Oregon Vital Records), "Effective January 1, 2026" (Oregon fee schedule, DL-06), "Fees effective May 6, 2026" (Utah, DL-08), and "Status as of March 6, 2026" (LegiScan, DL-05). These describe the version that was read on the `checked` date. They are not claims about today. A new form revision does not make page wording wrong unless the form's number or rules change. The evidence audit reports a new revision of a PDF form as a "bytes" change, and a person opens the form to see what changed.

## Closed

None yet.
