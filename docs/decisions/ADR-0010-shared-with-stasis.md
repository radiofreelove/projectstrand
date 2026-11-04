# ADR-0010: Shared conventions with The Stasis Project

- Status: accepted
- Date: 2026-11-03

## Context

The Strand Project and The Stasis Project are sibling guides by the same maintainer, built the same way: sourced facts checked by the build, the ODHS palette, Cloudflare Pages, and strict privacy headers. A review on November 3, 2026 found places where the two differed without a stated reason (license file names, link colors, where "Report a mistake" and the independence statement sit) and two leftover GitLab settings in the build. The maintainer asked that the two stay consistent in technical and design choices where practical, including the ODHS palette. The same record is kept in Stasis as [0012](https://github.com/radiofreelove/projectstasis/blob/main/docs/decisions/0012-shared-with-strand.md).

## Decision

Both projects follow these conventions. A change to one should be made in both, or recorded here as a difference.

| Area | Shared convention |
|---|---|
| Colors | The ODHS Brand Guidelines palette (form DE2022), as palette only: never ODHS names, logos, brandmarks, or typography rules ([ADR-0003](ADR-0003-palette-and-independence.md)). Text holds 7:1 contrast. |
| Independence | Every page says "Independent guide" in a banner near the top, and again in the footer. |
| Fonts | System fonts by default, `system-ui` first. Readers can choose Atkinson Hyperlegible Next (setting value `hyper`), served from the site itself. Same package, version (5.3.0), files, and SHA-256 values in each project's `fonts.lock.json` ([ADR-0007](ADR-0007-fonts.md)). |
| Links | One link color, visited or not. |
| Mistakes | "Report a mistake" in that banner opens the About page section `#report`. That section says reports and GitHub account names are public, then links to GitHub issues. |
| Licenses | `LICENSE` holds CC BY 4.0 (the writing, which is most of each project). `LICENSE-CODE` holds MIT. The footer names both, and the About page section `#license` explains reuse ([ADR-0008](ADR-0008-licenses.md)). |
| Privacy headers | Content Security Policy with `connect-src 'none'`, `form-action 'none'`, and `font-src 'self'`; `Referrer-Policy: no-referrer`. |
| Interactive tools | Each tool has a public note in plain words that lists every question and every rule: [PATH-LOGIC.md](../PATH-LOGIC.md) here, [checker-logic.md](https://github.com/radiofreelove/projectstasis/blob/main/docs/checker-logic.md) in Stasis. |
| Hosting | Code on GitHub, site on Cloudflare Pages' free tier ([ADR-0004](ADR-0004-hosting.md)). The build reads no GitLab settings. |

Differences kept on purpose:

| Strand | Stasis | Why |
|---|---|---|
| Builds on Cloudflare and downloads the font at build time | Commits the built site, including the font files | Each project's build model. Both pin the same checksums. |
| "Leave quickly" on every page | No "Leave quickly" button | Strand's readers may need to hide what they are reading from people in their household. |

Differences not yet decided (the maintainer's call):

- On Strand, nothing is saved unless the reader turns on "Remember." Stasis saves display settings automatically.
- Strand's dark theme and header band are deep indigo. Stasis's dark theme is black.

## Consequences

- Readers who use both sites find the same font option, link behavior, and reporting route.
- A reviewer can compare the two projects line by line using this table.
- Visited links no longer change color, so a reader cannot use color to see which links they already opened. The underline and the link color are unchanged.
