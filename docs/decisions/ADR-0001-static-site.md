# ADR-0001: A static site built by a short Python script

- Status: accepted
- Date: 2026-11-03

## Context

The site must be fast on old phones and slow connections, cheap or free to host, easy to audit, and safe. It has no accounts, no forms that submit data, and no server-side logic.

## Decision

Build plain HTML pages from Jinja2 templates with a single Python script (`build.py`). Store sources, facts, and page metadata as YAML in `data/`. Ship only HTML, one CSS file, and three small JavaScript files. Use relative links so the site works at any web address or subfolder.

## Consequences

- Any static host works: GitLab Pages, GitHub Pages, Cloudflare Pages, or a plain web server.
- Pages work with JavaScript turned off; JavaScript adds only conveniences.
- Contributors need Python 3 and two libraries, Jinja2 and PyYAML.
- The build can enforce rules (every cited source must exist) that a hand-written site could not.
