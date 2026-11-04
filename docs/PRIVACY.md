# Privacy and safety model

## Who we protect, and from what

| Risk | Example | Mitigation |
|---|---|---|
| Someone checks a shared device | A family member or partner looks at browser history or saved data | Only reading settings are saved without asking (text size, colors, spacing, font, short version: nothing about the reader's case); checkmarks only with "Remember"; "Forget everything" button; Leave quickly; advice on private browsing. The privacy page says a saved-settings entry shows the site was used, much like history |
| Someone sees the screen | A coworker walks by | Leave quickly button and Shift x3 shortcut, sticky at the top of every page |
| Third-party tracking | Ad networks or analytics recording visits | No third-party code at all; Content Security Policy blocks other origins |
| Referrer leakage | An official site learns the visitor came from a trans resource | `no-referrer` policy and `rel="noreferrer"` on every outside link |
| Data requests | Someone asks the project for visitor data | We collect none and do not request host logs |
| Public issue tracker | A reader shares case details when reporting a mistake | Blank issues are off; every template warns against personal details; maintainers redact on sight |
| Public issue tracker | A reader's GitHub account name, linked to a report on a trans legal guide, is public and may identify them | The banner's "Report a mistake" link opens the About page first, which says the report and account name are public before linking to GitHub. The maintainer chose to keep GitHub issues as the only route (2026-11-03), so the site stays free of server code |

## What the site stores

- Nothing on any server we control. The site is static files.
- In the reader's browser: reading settings (`strand:prefs`), saved when the reader changes one, as on The Stasis Project (ADR-0010). Only if the reader turns on "Remember my checklist": checklist checkmarks (`strand:checks`) and the remember flag (`strand:remember`); turning it off erases both. "Forget everything" erases all three.
- Path finder answers are never stored.

## What the host can see

The hosting service (Cloudflare Pages today) can see standard request data such as IP addresses, as nearly any web host can (inference: we have not reviewed Cloudflare's log retention for Pages). Cloudflare Web Analytics stays off; the Content Security Policy would also block its script. The project does not run analytics and does not ask the host for visitor data. If the site moves hosts, this file and the privacy page must be updated, and any host analytics must stay off (see ADR-0002 and ADR-0004).

## Leave quickly: honest limits

- It replaces the current page with weather.gov using `location.replace`, so Back does not return to that page.
- Other pages from this site visited earlier remain in browser history.
- It cannot erase anything. The privacy page says so in plain words.

## Contributor rules

- Never put personal case details in issues, pull requests, commits, or research notes.
- Never add analytics, embeds, external fonts, or third-party scripts. `tests/check_site.py` and the Content Security Policy will flag most attempts.
- Treat any request to add tracking as a policy change that needs a new decision record.
