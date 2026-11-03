# Research methodology

How every fact on The Strand Project is found, checked, dated, and labeled.

## 1. Source order

Use the highest available source and open it.

1. **Law:** statutes, session laws, and administrative rules from the legislature's or state's own site.
2. **Court materials:** official forms, instructions, and fee schedules from the state judicial branch.
3. **Agency materials:** pages and forms from the agency that does the work (vital records, DMV, Social Security).
4. **Legal aid and advocacy guides** (for example, WashingtonLawHelp, the ACLU, the Human Rights Campaign). Used when they explain something official sources do not. Labeled "Not official" on the site.
5. **Bill trackers and aggregators** (for example, LegiScan). Leads only. Labeled "Not official" when cited.
6. **Search snippets.** Never support for a claim. If a fact rests only on a snippet, it is labeled "Not confirmed."

## 2. The open-and-read rule

A source is cited only after someone opens it and reads the part that supports the claim. Quotes on the site are copied from text we opened. If a page blocks automated tools, we say so in the research log and either find the same fact in another official source or label it "Not confirmed."

## 3. Currency checks

Printed codes lag behind new laws. For every statute:

- Check the edition notes for later session laws (for example, ORS chapter notes pointing to 2026 Oregon Laws chapters).
- Read the session law itself, including its effective and operative dates and its applicability section.
- Check whether bills from the most recent session passed, using the legislature's own records where they load.
- Record what was checked and what could not be checked in the research memo.

We never describe a court case as "good law." When a case matters, we report its procedural status from the most recent source we opened and its date.

## 4. Status labels

Each entry in `data/sources.yml` has a `status`:

| Status | Meaning | Shown on the site as |
|---|---|---|
| `verified` | Official, opened, and read on the `checked` date | No label |
| `secondary` | Opened and read, but not an official government source | "Not official" |
| `unverified` | Could not be opened, or the detail was not found in an official source | "Not confirmed" |
| `linked` | A form or directory linked for convenience; no fact depends on it | No label |

Interpretation that goes beyond what a source says is marked "Our reading" on the site and "(inference)" in the research memos.

## 5. Facts that change

Fees, form numbers, addresses, and phone numbers live in `data/facts.yml`. Each fact names its sources. Pages pull facts with `fact("id")`, so one edit updates every page. The build fails if a page uses a fact or source that does not exist.

## 6. Freshness

Every source and page has a `checked` date. The build report lists anything older than 120 days (`max_source_age_days` in `data/site.yml`), and the weekly scheduled check warns. A re-check means opening the source again, comparing it with the site, updating the dates, and adding an entry to [AUDIT-LOG.md](AUDIT-LOG.md).

## 7. Choosing organizations to list

- Court self-help, government agencies, and legal aid programs come first.
- We read each organization's own materials before listing it.
- We do not list religious, faith-based, or spiritually framed programs. A borderline case, such as a secular program with a faith-based partner, goes to the maintainer to decide.
- We prefer options with posted prices and an online, email, or mail route over phone-only or "call for a quote" processes.

## 8. Privacy in research

No personal case details go into issues, pull requests, commits, or research notes. Corrections describe the rule or the source, never a person's case.

## 9. Review before release

Before a change is published it must pass the checks in [REVIEW-CHECKLIST.md](REVIEW-CHECKLIST.md). Before version 1.0, each state's content must be reviewed by a lawyer licensed in that state, and the site must be tested with trans, nonbinary, disabled, and neurodivergent people who are paid for their time.
