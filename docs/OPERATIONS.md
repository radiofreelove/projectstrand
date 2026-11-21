# Operations

Runbooks for keeping The Strand Project accurate and online.

## Update a fee or other fact

1. Open the official source and confirm the new value.
2. Edit the fact in `data/facts.yml`. Update the source's `checked` date in `data/sources.yml`.
3. Update `checked` for affected pages in `data/pages.yml`.
4. Run `python3 build.py` and the tests. Add an audit log entry.

## Re-check a source

The weekly source check (below) lists anything older than 120 days in its freshness report. For each one: open it, compare it with the site, update dates, fix content, and log it in `docs/AUDIT-LOG.md`. If you re-read a source whose evidence baseline is out of date, refresh its baseline too (see "The baseline").

## Weekly source check

`.github/workflows/weekly.yml` runs every Monday at 17:43 UTC, and by hand: in GitHub, open Actions, select "Weekly source check," and choose "Run workflow." It builds the site, then runs three checks, one after another:

| Check | Asks | Needs a person when |
|---|---|---|
| `tests/check_external_links.py` | Does each source still answer? | any address fails. Some government sites refuse scripts, so this means "open it," not "it is dead." |
| `tests/freshness.py` | Is any source or page `checked` date older than 120 days? | anything is due. |
| `tests/evidence_audit.py` | Does each source still say the same thing? | any source is "changed." |

If any of them needs a person, the workflow opens one GitHub issue labeled `automated-source-check` with all three reports. It never writes to the repository. Its permissions are contents read and issues write, nothing more.

Since 0.1.10-beta, the Monday schedule lives only here. The "Checks" workflow runs on pushes, pull requests, and by hand. It no longer runs on a schedule or runs the link check, so each source is asked once a week, not twice.

## Evidence audit

The link check asks whether a source still answers. The evidence audit asks whether it still says the same thing.

```sh
python3 build.py                                          # for the fact-to-page map
python3 tests/evidence_audit.py --report evidence-report.md
python3 tests/evidence_audit.py --only or-ojd-fees --report evidence-report.md
```

For every source in `data/sources.yml`, the tool reads the site's robots.txt and stays out if it is asked to. It asks for one address at a time, with a pause between requests, a 30-second time limit, and a user agent that names the project. It turns the reply into text it can compare, and compares a SHA-256 of that text with [data/evidence_baseline.yml](../data/evidence_baseline.yml).

- **A web page** is compared as text: the words a reader sees, with tags, scripts, and styles removed. The hash covers the words alone, in order. Where the lines break does not count, so a line that was only joined to the next or split in two is not a change, and the report's diff does not show it.
- **A PDF** is compared by its bytes, because the project's declared test tools include no PDF library. The baseline marks it `mode: bytes`. A change report for a PDF is lower-confidence: the same words saved again make new bytes. Open the file before you believe it.
- **A few pages print a line that changes on every load,** such as a server name or a random form label. The `VOLATILE` list in the tool names each one, and that line is dropped before hashing. The baseline entry says so in its `note`. Add to that list only after you see a line flip with no change a reader would notice.
- **A reply that is not all there is never compared.** Some servers close the connection partway through a reply, and Python then hands over the part that arrived without an error. So a reply shorter than the length it announced (its Content-Length) is cut short, and so is a PDF that announced no length and has no end-of-file marker. A cut-short reply is asked for once more, and then the source is unreachable. One gap is known: a web page that announces no length and simply stops cannot be told from a whole one.
- **A page that is not the source is never compared.** Some sites answer automated visitors with a page that checks for them ("Please wait while your request is being verified", a CAPTCHA), or with a page that has no words and sends the browser elsewhere. The same site can send the real page on one fetch and the check on the next. Either way the source is checker-blocked for that run. So is any reply with fewer than 50 words, whatever it says: the shortest source text in either project in November 2026 had 165 words, and the check pages had a dozen. A check page that was hashed would match itself the next week, and the source would be called unchanged although no one had read its words.

These are the comparison rules. They are the same, line for line, in The Stasis Project's audit, and a test in each project checks that. `RULES` in the tool numbers them (2 since November 16, 2026). See "The comparison rules" below before changing them.

### The guard on baseline writes

Every baseline write, from `--write-baseline` or `--carry-forward`, goes through the guard in [tests/guards.py](../tests/guards.py): the same block of code, line for line, in The Stasis Project's `tools/guards.py`, with a test in each project checking that. The guard prints a completeness diff (what the write would gain, lose, or change) and refuses the write, exit 3 with nothing written, if it would drop a hash, weaken an entry, shrink the count hashed under the current rules, or move the baseline's `written` date backward. (Strand's baseline carries its written date in a `# written:` line in the file header, stamped by the guarded write.) A write whose fetch found a different hash for a source is refused unless a person names that source: `--accept-change ID --reason TEXT`. The flag is refused when `GITHUB_ACTIONS` is set, so a scheduled run can never accept a change. The file is written atomically: a temporary file, read back and checked against what was meant to be written, then renamed over the old one, so a write stopped partway leaves the old file whole.

Two offline checks use the same guard. `python3 tests/guards.py --reconcile` prints the registry against the baseline as one equation (sources = hashed under the current rules + hashed under older rules + checker-blocked with no hash + unreachable with no hash) and exits 3 if it does not add up. A merge-gate job in the checks workflow compares a pull request's offline health vector (registry size, sources hashed under the current rules, facts resting on a hashed source) with the main branch's, and fails on any decrease the pull request's body does not accept in so many words: `Accepted decrease: <measure>, <from> to <to>, because <reason>`.

### The four states

Every source ends in exactly one.

| State | What it means | What to do |
|---|---|---|
| Unchanged | The content matches the baseline. | Nothing. |
| Changed | The content differs. For a web page, the report shows what changed, up to a limit. It names the facts in `data/facts.yml` that cite the source, and the pages that show those facts. It also names pages that cite the source directly. | Re-read the source. A change is a prompt to read, not proof that a fact is wrong: a new menu item changes a page too. If a fact changed, follow "Update a fee or other fact." Then refresh that source's baseline. |
| Unreachable | The connection failed, the reply was cut short twice (including a reply shorter than the length it announced), or the server answered with an error other than 401 or 403. Nothing was compared. | Look at the link check report in the same issue. If the address keeps failing there, open it by hand. |
| Checker-blocked | The site answered 401 or 403 to this tool, its robots.txt keeps this tool out, or the site answered with a check for automated visitors (or a page with no words, or fewer than 50) instead of the source. | A person opens it. This state says nothing about the source. It is not a dead link, and it is not a removed source. |

Why the care with "checker-blocked": on November 14, 2026, a person opened by hand all 8 sources the link check had flagged. Every one was alive for a human reader.

The report has one more list, **Not yet baselined**: sources with no stored hash. They were blocked or unreachable when the baseline was written, or they were added since, or their address changed, or their hash was written under older comparison rules. A missing hash is never counted as a change.

Only a changed source fails the run (exit code 1). Blocked and unreachable sources are listed in the report and do not fail the run. An address that keeps failing shows up in the link check, which does fail.

The pages each fact appears on come from the build. `build.py` lists the facts each page rendered in `public/build-report.json`, and the audit reads that file. Without a build, the report still names the facts and says the pages are not known.

### The baseline

- **What the baselines rest on.** The baselines rest on the project's November 2026 verified source checks. Each entry copies the source's `checked` date from `data/sources.yml` on the day it was written (`registry_checked`). That check is what stands behind the hash.
- **What the baseline run was not.** The run that wrote the baseline on November 15, 2026 was a tool fetching each address and storing a hash. The November 17 carry-forward fetched nothing. Neither was a fresh read of every source by a person, and nothing here says it was.
- **What it holds.** One entry per source: its address, the fetch date, the fetch state, the comparison mode (`text` or `bytes`), the SHA-256, the length, `registry_checked`, and `rules`, the comparison rules the hash was taken under. An entry marked `carried` was re-hashed from the saved text of an earlier fetch, without fetching again. An entry written again from a fresh fetch says, under `earlier`, whether that fetch said the same as the hash it replaced. On November 15, 2026: 44 of 59 sources were read (29 as text, 15 as bytes), 11 were checker-blocked, and 4 were unreachable. The 15 with no hash are "not yet baselined." Two compare runs right after the baseline found 44 unchanged and 0 changed.
- **November 17, 2026: carried forward to rules 2.** The 29 web pages were re-hashed under the new comparison rules from the text saved on November 15, with no new fetch. The baseline still holds what each one said on November 15. Nothing new was taken in, so the change the November 16 audit found on `or-ojd-forms` is still reported until a person reads it. The 15 PDFs were not carried forward. A PDF's hash cannot be re-taken without its bytes, which are not saved, and the old rules hashed a reply cut short as if whole. Their November 15 hashes stay in the baseline under rules 1, so they are "not yet baselined" until they are written again with `--write-baseline --only ID`. That run says whether each PDF is the same file as on November 15. If it is, that also shows the November 15 reply was whole, and the entry rests on the same source check as before.
- **Hashes, not text.** The repository does not keep copies of official pages. To show what changed, the tool keeps each page's text in `.evidence-snapshots/`, which is not committed. The weekly run saves that folder between runs. If the saved text is gone, the report still names the changed source, its facts, and its pages, and says there is no diff to show.
- **Refresh a baseline only on purpose.** Comparing never rewrites it. Refresh one source after a person has re-read it and its `checked` date is set:

  ```sh
  python3 tests/evidence_audit.py --write-baseline --only or-ojd-fees
  ```

  Do the same to give a "not yet baselined" source its first hash, after a person has read it. Never refresh a baseline to make a "changed" report go away without reading the source. A refresh keeps the old hash for any source it cannot read that day, even one written under older rules. For each source it can read, it says whether the source still says what its old hash said: "the same" carries the old entry's verified check forward; "different", "not known", or a first hash means a person reads the source before the new hash is relied on. Say what you refreshed, and why, in [AUDIT-LOG.md](AUDIT-LOG.md).

### The comparison rules

The comparison rules turn a reply into what is hashed: what counts as the words of a page, which replies are cut short, and which replies are not the source. They are one block in `tests/evidence_audit.py`, marked "The comparison rules (begin)" and "(end)", and the same block is in The Stasis Project's `tools/evidence_audit.py`. Each project's tests hold the block's SHA-256 (`RULES_BLOCK_SHA256`), so a change in one project fails its tests until the same change is made in the other and both hashes are updated. The `VOLATILE` list sits outside the block, because each project's sources are its own.

They are shared because a baseline written on one computer is compared with fetches made on another. In November 2026, The Stasis Project's baseline was captured on a computer that broke lines in other places and hashed replies that were cut short, and 42 of its sources looked changed when they were not.

`RULES` numbers the rules. Raise it whenever a change would change a hash. Every baseline entry records the `rules` it was written under, and an entry under other rules is never compared: it is "not yet baselined", never "changed". To bring the baseline under new rules:

- **Carry forward** what you can, without fetching anything. This re-hashes each entry from the text saved when it was written, so the baseline still holds what the source said then, and a real change since is still reported:

  ```sh
  python3 tests/evidence_audit.py --carry-forward
  ```

  It refuses an entry whose saved text is not on this computer, or is a check for automated visitors or too short to be the source. It never carries a PDF forward: there is no saved copy to re-take the hash from, and under rules 1 a reply cut short was hashed as if whole (9 of The Stasis Project's 37 PDF hashes on November 15, 2026). Carrying forward also cannot tell whether a saved text was itself cut short, so carry an entry forward only when something shows its saved text was whole (a later fetch matched it, or differed from it in only a few words). Every one of this project's 29 carried pages matched a fetch on November 16 or, for `or-ojd-forms`, differed by one menu line.
- **Write the rest again** with `--write-baseline --only ID`. It says, for each source, whether the new hash says what the old one said; read any source that is not "the same" before relying on its new hash, as above.

The tests run against files in `tests/fixtures/evidence/` and a small server on your own computer. They never use the live network:

```sh
python3 tests/test_evidence_audit.py
python3 tests/test_mechanical_update.py
```

## Dated language

[dated-language.md](dated-language.md) lists the wording on the site that depends on the date: "New in 2026," "What changed in 2026," the 2026 fee schedules, the Orr v. Trump status, and more. Each entry gives the exact words, where they appear, when they expire, and what to do then.

`tests/freshness.py` and `data/site.yml` have no checkpoint mechanism, so that file is the register. No scheduled check reads it. Look at it at the start of each month and whenever the weekly source check opens an issue. The first dates fall on January 1, 2027.

## Mechanical date updates

`tests/mechanical_update.py` is built, tested, and **not switched on**. Nothing runs it on a schedule.

```sh
python3 tests/evidence_audit.py --report evidence-report.md --results evidence-results.json
python3 tests/mechanical_update.py --audit evidence-results.json --dry-run
```

Given an evidence audit run, it sets the `checked` date in `data/sources.yml` to the audit's date for exactly the sources the audit found unchanged, and nothing else. It changes only those lines, keeps every comment, and prints every date it changed. It refuses, and writes nothing, for a source named with `--only` that is changed, checker-blocked, unreachable, or not yet baselined; for a hash, address, or baseline that does not agree; and for an audit that is more than 2 days old, dated in the future, or malformed. A date never moves backward. `--dry-run` writes nothing.

It is ready to wire into the weekly workflow behind a repository variable switch, as The Stasis Project does: a second job that runs only when the variable `MECHANICAL_UPDATES` is `on`, with `contents: write` and `pull-requests: write` for that job alone. It would open a pull request for a person to review and never merge anything.

Before anyone turns it on, settle one question. The site says "We read each of these on the date shown" under every page's source list, and the sources page says "We read each one ourselves on the date shown." `data/sources.yml` defines `verified` as "We opened and read it on the 'checked' date." A date set by this tool means a tool found the same content as the last verified check, not that a person read the source again. Either that wording changes, or the tool writes a different field, before its dates can appear on the site.

## Add a source

Add an entry to `data/sources.yml` (id, title, short, publisher, url, kind, jurisdiction, date, checked, status, notes). Cite it in a template with `{{ src('id') }}` or link it with `{{ ext('id') }}`. The build fails if the id is wrong.

## Publish

Cloudflare Pages builds and publishes every push to `main`.

First-time setup in the Cloudflare dashboard ([Cloudflare Docs](https://developers.cloudflare.com/pages/get-started/git-integration/)):

1. Workers & Pages, then Create application, then Pages, then Connect to Git.
2. Choose GitHub, authorize if asked, and pick `radiofreelove/projectstrand`.
3. Project name: `projectstrand`. Production branch: `main`.
4. Framework preset: None. Build command: `bash scripts/cloudflare_build.sh`. Build output directory: `public`.
5. Save and Deploy. The site appears at `https://projectstrand.pages.dev` if that name is free. If Cloudflare assigns a different address, add an environment variable `SITE_URL` with the real address, or update `public_url` in `data/site.yml`.

After setup, leave Web Analytics off for this project (ADR-0002).

Spacefast is an active secondary publishing target alongside Cloudflare Pages. On every push to `main` (and on manual workflow dispatch), `.github/workflows/deploy-spacefast.yml` builds the Spacefast theme with `python3 build.py --theme spacefast --out public-spacefast`, runs `contrast.py` and `check_site.py`, and publishes with `sf publish` using the `SPACEFAST_TOKEN` and `SPACEFAST_SPACE` repository secrets.

## Update the fonts

`fonts.lock.json` pins the font package version and each file's SHA-256. To update: change `version`, set each `sha256` to `null`, push, copy the new values from the build log, and push again with an audit log entry.

## Update Playwright

A Playwright update is always one commit that changes `test-tools/requirements.txt`, `test-tools/package.json`, and the axe job's container tag in `.github/workflows/checks.yml` together (`tests/check_versions.py` fails otherwise). Make that commit by hand, and close Dependabot's separate Playwright pull requests; Dependabot closes them on its own once the version is on `main`.

## Run checks by hand

In GitHub, open Actions, select "Checks," and choose "Run workflow." For the external link report, the freshness report, and the evidence audit, run "Weekly source check" the same way.

## Automated workflows

- `.github/workflows/checks.yml`: builds and checks the site on pushes and pull requests.
- `.github/workflows/weekly.yml`: runs the weekly external link, freshness, and evidence audit checks.
- `.github/workflows/deploy-spacefast.yml`: builds and publishes the Spacefast theme on pushes to `main` and on manual dispatch.
- `.github/workflows/release.yml`: after Checks pass on a push to `main`, tags the commit and publishes a GitHub release if the version in `data/site.yml` has no tag yet (using that version's entry in `CHANGELOG.md`).
- `.github/workflows/live.yml`: runs `tests/check_live.py` against the deployed site.

## Move hosts

See [decisions/ADR-0004-hosting.md](decisions/ADR-0004-hosting.md) and [decisions/ADR-0011-spacefast-secondary-host.md](decisions/ADR-0011-spacefast-secondary-host.md).
