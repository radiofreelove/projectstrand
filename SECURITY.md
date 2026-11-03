# Security

## Report a vulnerability

Use GitHub's private vulnerability reporting for this repository (Security tab, "Report a vulnerability") if it is turned on. Otherwise, open an issue that says only that you found a security problem and how to reach you; do not post the details publicly. Do not include anyone's personal data.

## What matters most here

The site holds no accounts and collects no data, so the main risks are:

- Anything that could make a reader's visit visible to someone else: third-party requests, referrer leaks, or saved data without consent.
- Content injection: a change that adds scripts or styles the Content Security Policy should block.
- Supply chain: a tampered font file or build dependency.

## Built-in protections

- A strict Content Security Policy (`script-src 'self'`, `style-src 'self'`, `connect-src 'none'`, `form-action 'none'`, `frame-ancestors 'none'`), sent as an HTTP header by Cloudflare Pages through `site-root/_headers` and repeated in each page's `<meta>` tag.
- Other headers from `site-root/_headers`: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cross-Origin-Opener-Policy`, and a `Permissions-Policy` that turns off camera, microphone, location, and similar features.
- `no-referrer` policy and `rel="noreferrer"` on every outside link.
- No inline scripts, styles, or event handlers; `tests/check_site.py` fails if any appear.
- Pinned build dependencies; font files checked against SHA-256 values in `fonts.lock.json` once pinned.

## Known gaps

- Python package hashes are not pinned yet.
- The `<meta>` copy of the policy cannot set `frame-ancestors`; that protection depends on the host sending `_headers`. Any new host must send equivalent headers.
