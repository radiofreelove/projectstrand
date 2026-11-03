# ADR-0004: Code on GitHub, site on Cloudflare Pages

- Status: accepted (supersedes the earlier GitLab Pages plan)
- Date: 2026-11-03

## Context

The beta was first prepared for GitLab and GitLab Pages. Before anything was pushed, the maintainer deleted the GitLab project and chose GitHub for the code and Cloudflare's free Pages hosting for the site. The project's public name stays The Strand Project on every page and document; `projectstrand` appears only in web addresses.

## Decision

- **Code and audit trail:** `github.com/radiofreelove/projectstrand`.
- **Site:** a Cloudflare Pages project named `projectstrand`, connected to the GitHub repository through Cloudflare's Git integration. Cloudflare builds every push to `main` with `bash scripts/cloudflare_build.sh` and publishes the `public` folder. The intended address is `https://projectstrand.pages.dev`.
- **Checks:** GitHub Actions (`.github/workflows/checks.yml`) runs the build, structure, contrast, reading-level, browser, and axe-core checks on every push and pull request, plus a weekly freshness and link report. The Cloudflare build also runs the fast checks, so a broken build fails before it deploys.
- **Clean URLs:** Cloudflare redirects `/page.html` to `/page` ([Cloudflare Docs](https://developers.cloudflare.com/pages/configuration/serving-pages/)). The Cloudflare build therefore writes links without `.html` (`CLEAN_URLS=1`, also triggered by Cloudflare's `CF_PAGES=1`), which saves a redirect on every click.
- **Security headers:** `site-root/_headers` sends the Content Security Policy and related headers ([Cloudflare Docs](https://developers.cloudflare.com/pages/configuration/headers/)).
- **Host-neutral build:** `build.py` reads the site address from `SITE_URL`, then `public_url` in `data/site.yml`, and the repository from `REPO_URL`, GitHub Actions variables, or `repo_url`.

## Why Git integration instead of deploying from GitHub Actions

Git integration needs no API tokens stored in GitHub, and Cloudflare's docs support private and public repositories. The trade-off is that the browser and axe-core checks in GitHub Actions do not block a deploy; the fast checks in the Cloudflare build do. Cloudflare's docs also say a project created with Git integration cannot switch to Direct Upload later ([Cloudflare Docs](https://developers.cloudflare.com/pages/get-started/git-integration/)). If gated deploys become necessary, turn off automatic deployments and deploy from GitHub Actions with Wrangler.

## Free plan limits that matter

500 builds a month, one build at a time, a 20-minute build timeout, and up to 20,000 files per site ([Cloudflare Docs](https://developers.cloudflare.com/pages/platform/limits/)). This site uses about 30 files and builds in well under a minute (inference).

## Consequences

- Moving hosts again changes configuration, not code.
- Cloudflare features that inject scripts or tracking (Web Analytics, and email address obfuscation on custom domains) must stay off, per ADR-0002. The Content Security Policy blocks injected scripts, which would also break features that depend on them.
