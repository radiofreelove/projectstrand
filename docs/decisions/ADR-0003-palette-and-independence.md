# ADR-0003: An ODHS-inspired palette, with clear independence

- Status: accepted, pending maintainer review of the independence questions below
- Date: 2026-11-03

## Context

The maintainer asked for colors in the style of the Oregon Department of Human Services. The ODHS Brand Guidelines (form DE2022, July 2025) publish a palette and tested contrast pairs. The same guidelines restrict use of ODHS names, logos, and brandmarks, and say that materials "representing ODHS" must follow agency policy 130-001. ([ODHS Brand Guidelines PDF](https://sharedsystems.dhsoha.state.or.us/DHSForms/Served/dhs2022.pdf))

## Decision

- Use the palette's colors only: North Star Indigo #2E3192, Glacial Blue #B4DCF5, Fog Gray #F4F2ED, Forest Green #184E49, Willamette Green #86C679, Mist Grey #D8E1E5, Marionberry Red #A91F50, Harvest Gold #ECD263, Desert Sand #EDDFD4, Ashland Charcoal #414042, black, and white, plus tints of these for backgrounds.
- Do not use ODHS names, logos, brandmarks, typography rules, or templates on the site.
- Do not mention ODHS on the public site, including its data files. The palette's origin is recorded only here and in the `brand-odhs` entry of `data/sources.yml`, which is marked `docs_only` and left out of the published `sources.json`.
- Show an independence statement in every page footer: "not run by, or connected to, any court or government agency."
- Verify contrast in code (`tests/contrast.py`) rather than relying on published pairs, because tints and dark-mode colors are our own.

## Open questions for the maintainer

- Colors alone are not a brandmark, but a familiar palette can still suggest a connection to an agency. Before launch, the maintainer confirms that using these colors raises no conflict with any agency or employer rules.
- Any change to the palette must keep every pair passing `tests/contrast.py`.

## Consequences

The site feels calm and trustworthy, meets AAA contrast for reading text in every theme, and makes no claim of affiliation.
