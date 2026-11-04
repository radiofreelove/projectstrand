# Dependencies and licenses

## Shipped to readers

| What | Why | License |
|---|---|---|
| Our HTML, CSS, JavaScript, and mark | The site | MIT |
| Our writing | The guide | CC BY 4.0 |
| Atkinson Hyperlegible Next (optional, fetched at build) | Easy-to-read font option | SIL Open Font License 1.1; license text saved beside the font files |

No other code, fonts, images, or services are shipped to readers. How to reuse our own code and writing: [REUSING.md](REUSING.md).

## Used only to build and test

| What | Version | License |
|---|---|---|
| Python | 3.13 (GitHub Actions and the Cloudflare Pages v3 build image) | PSF License |
| GitHub Actions: checkout, setup-python, upload-artifact, download-artifact | v7, v7, v7, v8 | MIT |
| Jinja2 | 3.1.6 | BSD-3-Clause |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| PyYAML | 6.0.3 | MIT |
| Playwright and Chromium (browser tests) | 1.64.1 | Apache-2.0 (Playwright) |
| axe-core (accessibility tests) | 4.14.0 | MPL-2.0 |

Versions are pinned in `requirements.txt` (build), `test-tools/requirements.txt` and `test-tools/package.json` (test tools, the same versions as The Stasis Project), `.python-version`, `.github/workflows/checks.yml`, and `fonts.lock.json`. Dependabot proposes updates monthly for the GitHub Actions, both requirements files, and `test-tools/package.json`. The axe job's container tag in `checks.yml` must match Playwright's version; `tests/check_versions.py` fails until it does. The test tools sit in `test-tools/`, not the repository root, because Cloudflare Pages installs any `package.json` it finds at the root on every deploy ([Cloudflare docs: Build image](https://developers.cloudflare.com/pages/configuration/build-image/), updated Oct. 26, 2026). Python package hashes are not pinned yet; that is a known gap.
