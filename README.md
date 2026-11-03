# The Strand Project

**Changing your name or gender marker should not take a lawyer, a law degree, or luck.**

The Strand Project is a free, plain-language guide to changing your legal name and gender marker in Oregon, Washington, and Utah. It walks people through the whole path, from court to Social Security to the DMV to the birth certificate office, in the right order, with a link to every official form and a date on every fact.

It is independent. It is not run by, or connected to, any court or government agency.

- **Site:** https://projectstrand.pages.dev (Cloudflare Pages)
- **Source and audit trail:** https://github.com/radiofreelove/projectstrand

> Status: **beta, version 0.1.0-beta.** Content was checked against official sources on November 3, 2026. It has not yet been reviewed by a lawyer licensed in each state. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Why this exists

In the 2022 U.S. Trans Survey, 48% of respondents with at least one ID said none of their IDs listed the name they wanted, and 59% said none listed the gender they wanted. 22% of all respondents reported being harassed, assaulted, asked to leave, or denied service after showing an ID that did not match their presentation. ([NCTE, Early Insights, February 2024](https://ustranssurvey.org/wp-content/uploads/2023/11/2022-USTS-Early-Insights-Report_FINAL.pdf))

The process to fix that is split across courts and agencies that each explain only their own step. This project explains the whole path. The full statement is in [docs/VISION.md](docs/VISION.md).

## What is in this repository

| Path | What it is |
|---|---|
| `templates/` | Page templates (Jinja2). The words on the site live here. |
| `data/sources.yml` | Every source: URL, publisher, version date, the date we checked it, and its status. |
| `data/facts.yml` | Numbers that change, like fees, each tied to its source. |
| `data/pages.yml`, `data/site.yml` | Page list and site settings. |
| `static/` | CSS, JavaScript, and the favicon. No third-party code. |
| `scripts/make_mark.py` | Draws the mark (the header logo and the favicon). |
| `build.py` | Builds the site into `public/`. Fails if a page cites a source or fact that does not exist. |
| `tests/` | Structure, contrast, reading level, browser, axe-core, freshness, and link checks. |
| `docs/` | Vision, methodology, research memos, decisions, accessibility, privacy, and the audit log. |
| `.github/` | GitHub Actions checks, issue and pull request templates, and Dependabot settings. |
| `scripts/cloudflare_build.sh` | The build command Cloudflare Pages runs before each deploy. |
| `site-root/_headers` | HTTP security headers for Cloudflare Pages. |

## Build it yourself

```sh
pip install -r requirements.txt
python3 build.py                  # writes public/
python3 tests/check_site.py       # structure, links, labels, CSP safety
python3 tests/contrast.py         # every color pair in every theme
python3 tests/readability.py      # reading level and long sentences
python3 tests/browser_checks.py   # needs Playwright and Chromium
```

Open `public/index.html` in a browser, or run `python3 -m http.server -d public`.

Optional: `python3 scripts/fetch_fonts.py` downloads the Atkinson Hyperlegible Next font so the "easy-to-read font" setting appears.

Publishing: Cloudflare Pages runs `bash scripts/cloudflare_build.sh` on every push to `main` and serves the `public` folder. Setup steps are in [docs/OPERATIONS.md](docs/OPERATIONS.md).

## How the sausage is made

Everything behind the site is public on purpose, so anyone can check the work.

- **Research memos:** [Oregon](docs/research/oregon.md), [Washington](docs/research/washington.md), [Utah](docs/research/utah.md), [federal](docs/research/federal.md). Each one lists the issue, the short answer, the authority, what is uncertain, and a research log of what we opened and what we could not.
- **Method:** [docs/METHODOLOGY.md](docs/METHODOLOGY.md) explains how sources are chosen, checked, dated, and labeled.
- **Decisions:** [docs/decisions/](docs/decisions/) records why the site is built the way it is.
- **Audit log:** [docs/AUDIT-LOG.md](docs/AUDIT-LOG.md) records every research pass, check, and release.
- **Accessibility:** [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md). **Privacy:** [docs/PRIVACY.md](docs/PRIVACY.md). **Writing style:** [docs/CONTENT-STYLE.md](docs/CONTENT-STYLE.md).
- **Running it:** [docs/OPERATIONS.md](docs/OPERATIONS.md) covers publishing, updating a fee, re-checking sources, and moving hosts.

## Report a mistake or help

Open an issue on GitHub and pick a template. Please do not include personal details about your own case. See [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).

## License

- **Writing** (the words on the site and in this repository's documents): [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-CONTENT).
- **Code** (build scripts, tests, CSS, JavaScript, and template markup): [MIT License](LICENSE).

You can copy, share, and adapt the guide. Credit us like this: "The Strand Project (https://projectstrand.pages.dev), CC BY 4.0." [docs/REUSING.md](docs/REUSING.md) explains what each license covers, how to credit us, and what neither one covers. Third-party tools and fonts are listed in [docs/DEPENDENCIES.md](docs/DEPENDENCIES.md).

## Not legal advice

We explain the process. We are not your lawyer. For advice about a specific situation, see the help page on the site.
