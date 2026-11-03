# ADR-0002: No tracking, no third parties, consent-only storage

- Status: accepted
- Date: 2026-11-03

## Context

Readers may be closeted, in unsafe homes, on shared devices, or worried about government data use. Even "harmless" analytics would record that someone looked up how to change a gender marker.

## Decision

- No cookies, analytics, ads, social buttons, third-party scripts, or third-party fonts.
- A Content Security Policy in every page blocks connections to any other origin (`connect-src 'none'`, everything else `'self'`).
- `referrer` policy `no-referrer`, and `rel="noreferrer"` on every outside link, so official sites do not learn that a visitor came from here.
- Reading settings and checklists are kept in memory only, unless the reader turns on "Remember." "Forget everything" erases all saved data.
- A Leave quickly button and a Shift-key-three-times shortcut replace the page with a weather site.
- The path finder never sends or saves answers.

## Consequences

- We cannot count visitors. Success is measured by feedback, issues, and partner organizations, not analytics.
- If the site moves to a host that offers analytics (for example, Cloudflare), those features must stay off. See [ADR-0004](ADR-0004-hosting.md).
- Tests check for inline scripts, inline styles, and missing `noreferrer`, which the policy would otherwise break or leak.
