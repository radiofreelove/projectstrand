# Operations

Runbooks for keeping The Strand Project accurate and online.

## Update a fee or other fact

1. Open the official source and confirm the new value.
2. Edit the fact in `data/facts.yml`. Update the source's `checked` date in `data/sources.yml`.
3. Update `checked` for affected pages in `data/pages.yml`.
4. Run `python3 build.py` and the tests. Add an audit log entry.

## Re-check a source

The weekly scheduled run of the "Checks" workflow lists anything older than 120 days in its freshness step. For each one: open it, compare it with the site, update dates, fix content, and log it in `docs/AUDIT-LOG.md`.

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

## Pin the fonts

The first build with network access prints a SHA-256 for each font file in its log (GitHub Actions or Cloudflare). Copy each value into `fonts.lock.json`, and replace `"version": "5"` with the exact version jsDelivr served. Commit with an audit log entry.

## Run checks by hand

In GitHub, open Actions, select "Checks," and choose "Run workflow." This also runs the external link report.

## Move hosts

See [decisions/ADR-0004-hosting.md](decisions/ADR-0004-hosting.md).
