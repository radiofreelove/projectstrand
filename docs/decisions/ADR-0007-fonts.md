# ADR-0007: System fonts by default, optional Atkinson Hyperlegible Next

- Status: accepted
- Date: 2026-11-03

## Context

Atkinson Hyperlegible Next, from the Braille Institute, is designed so similar letters are easy to tell apart. Loading it from a font service would leak visits to a third party (see ADR-0002). Committing font binaries through the tools used to build this beta was not practical, and the build environment could not download them.

## Decision

- The default font is the reader's own system font: fast, familiar, and private.
- `scripts/fetch_fonts.py` downloads Atkinson Hyperlegible Next (regular and bold, Latin subset) from the Fontsource package on jsDelivr during each build, plus its SIL Open Font License text. When the files exist, the build adds a Reading settings option to use the font.
- `fonts.lock.json` records each file's SHA-256. The first successful build with network access (GitHub Actions or Cloudflare) prints the hashes; a maintainer copies them into the lock file and replaces the major version (`5`) with the exact version. After that, a changed file fails the build.
- A download failure (no network) does not fail the build; the site uses system fonts.

## Consequences

- Until hashes are pinned, the font is trusted on first use. This is recorded as an open item in the audit log.
- The font is self-hosted, so readers' browsers never contact a font service.
