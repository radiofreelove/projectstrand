# Contributing to The Strand Project

Thank you for helping. Accuracy and safety come first, so every change follows the same steps.

## Before you start

- **Never include personal case details** in issues, pull requests, or commits: no names, birth dates, addresses, case numbers, or medical information. Describe the rule or the source, not a person.
- Read [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and [docs/CONTENT-STYLE.md](docs/CONTENT-STYLE.md).

## Report a problem

Open an issue and pick a template:

- **Correction**: something on the site is wrong or out of date.
- **Source update**: an official form, fee, or page changed.
- **Accessibility**: something is hard to use.
- **New state**: a request to cover another state.

## Change the site

1. Make a branch.
2. Edit templates in `templates/pages/`, sources in `data/sources.yml`, or values in `data/facts.yml`.
3. Run:
   ```sh
   python3 build.py
   python3 tests/check_site.py
   python3 tests/contrast.py
   python3 tests/readability.py
   python3 tests/browser_checks.py
   ```
4. Update the research memo, the audit log, and the changelog as the review checklist asks.
5. Open a pull request. The template includes [the review checklist](docs/REVIEW-CHECKLIST.md).

## What we will not merge

- Legal advice or recommendations about what a person should choose.
- Facts without an opened source, or quotes from text nobody opened.
- Tracking, analytics, embeds, external fonts, or third-party scripts.
- Listings of religious or faith-based programs (see the methodology).

## Conduct

Everyone follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licensing your contribution

When you contribute, you agree to share your work under the project's licenses: writing under [CC BY 4.0](LICENSE) and code under the [MIT License](LICENSE-CODE). Only contribute work you wrote or have the right to share. See [docs/REUSING.md](docs/REUSING.md).
