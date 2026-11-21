# ADR-0011: Spacefast as an active secondary host

- Status: accepted
- Date: 2026-11-20

## Context

Cloudflare Pages (`https://projectstrand.pages.dev`) is the primary public host for Project Strand, as recorded in `ADR-0004-hosting.md`. Having an active secondary host gives readers a working mirror and lets us maintain a Spacefast-themed build without disturbing the primary site.

## Decision

Keep Cloudflare Pages (`https://projectstrand.pages.dev`) as the primary host, and publish Spacefast as an active secondary host from `main` (and manual workflow runs) via `.github/workflows/deploy-spacefast.yml`.

The workflow builds a Spacefast-themed output directory (`python3 build.py --theme spacefast --out public-spacefast`), runs the contrast and site checks (`tests/contrast.py` and `tests/check_site.py`), installs `spacefast@0.10.0`, and publishes the build using `sf publish` with the `SPACEFAST_TOKEN` and `SPACEFAST_SPACE` secrets.

## Consequences

- **Independent copy:** The Spacefast site is a separate, independent copy of the built site rather than a redirect or proxy to Cloudflare Pages.
- **No tracking:** Like the primary site, the Spacefast-hosted build keeps the no-tracking rule intact.
- **Secrets in GitHub Actions:** Publishing to Spacefast relies on `SPACEFAST_TOKEN` and `SPACEFAST_SPACE` stored as GitHub Actions secrets.
