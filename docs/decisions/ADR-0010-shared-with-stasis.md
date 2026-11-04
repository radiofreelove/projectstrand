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
| Mistakes | "Report a mistake" in that banner opens the About page section `#report`. That section says reports and GitHub account names are public, then links to GitHub issues. GitHub issues are the only reporting route: the maintainer chose not to add a form (Nov. 3, 2026), which keeps both sites free of server code. |
| Saved settings | Display or reading settings are saved on the device automatically when the reader changes one. A reset or "Forget everything" control erases them. Strand's checklist checkmarks are still saved only if the reader turns on "Remember my checklist." |
| Licenses | `LICENSE` holds CC BY 4.0 (the writing, which is most of each project). `LICENSE-CODE` holds MIT. The footer names both, and the About page section `#license` explains reuse ([ADR-0008](ADR-0008-licenses.md)). |
| Security headers | Identical on both sites (Nov. 3, 2026): Content Security Policy `default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; object-src 'none'; frame-ancestors 'none'` (the same policy, without `frame-ancestors`, in each page's meta tag); `Referrer-Policy: no-referrer`; `X-Content-Type-Options: nosniff`; `X-Frame-Options: DENY`; `Permissions-Policy` blocking accelerometer, browsing-topics, camera, geolocation, gyroscope, magnetometer, microphone, payment, and usb; `Cross-Origin-Opener-Policy: same-origin`; `Strict-Transport-Security: max-age=31536000` (no effect on pages.dev, where the whole .dev domain is already HTTPS-only; it matters on a custom domain). `tests/check_site.py` here and `tools/check_structure.py` in Stasis fail if they change. |
| Tool pages | A tool page lists every source it uses. When the list is long, it starts closed behind a "Show all" toggle, because each result line links its own source (Strand's path finder, 24 sources). Stasis's check lists its 6 openly. |
| Code of conduct | The same `CODE_OF_CONDUCT.md`, adapted to each site's readers. To report a problem, a person opens an issue that says only that they need to report one; the maintainer replies with a private way to talk. Nobody is asked to post contact details in public. |
| Interactive tools | Each tool has a public note in plain words that lists every question and every rule: [PATH-LOGIC.md](../PATH-LOGIC.md) here, [checker-logic.md](https://github.com/radiofreelove/projectstasis/blob/main/docs/checker-logic.md) in Stasis. |
| Hosting | Code on GitHub, site on Cloudflare Pages' free tier ([ADR-0004](ADR-0004-hosting.md)). The build reads no GitLab settings. |

Differences kept on purpose:

| Strand | Stasis | Why |
|---|---|---|
| Uppercase doc names (`PRIVACY.md`) and ADR numbering (`ADR-0010-...`) | Lowercase doc names (`design.md`) and numbered decisions (`0012-...`) | Renaming would break links into the docs. The paired records link across. |
| Builds on Cloudflare and downloads the font at build time | Commits the built site, including the font files | Each project's build model. Both pin the same checksums. |
| "Leave quickly" on every page | No "Leave quickly" button | Strand's readers may need to hide what they are reading from people in their household. |

Each site's dark theme keeps its own background, by the maintainer's choice of November 3, 2026: deep indigo for Strand and black for Stasis. Both names nod to Destiny 2 powers. Strand's color there is green, which lives in the mark's thread; the indigo comes from the ODHS palette. Stasis's color there is icy blue, so its dark theme shows glacial blue headings and links on black. Both themes hold text at 7:1, and neither uses color alone to carry meaning: callouts have titles, and the current page is marked by an underline, not only color.

## Consequences

- Readers who use both sites find the same font option, link behavior, and reporting route.
- A reviewer can compare the two projects line by line using this table.
- Visited links no longer change color, so a reader cannot use color to see which links they already opened. The underline and the link color are unchanged.
