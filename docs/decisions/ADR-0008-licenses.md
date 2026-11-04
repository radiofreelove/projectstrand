# ADR-0008: MIT for the code, CC BY 4.0 for the writing

- Status: accepted; file names changed by [ADR-0010](ADR-0010-shared-with-stasis.md)
- Date: 2026-11-03

## Context

The guide is most useful if others can reuse it: legal aid groups, court self-help centers, schools, and people writing guides for other states. The first beta proposed two licenses, one for the code and one for the writing, and left the choice to the maintainer. On November 3, 2026, the maintainer chose to adopt them.

GitHub labeled the repository's license "Other." The cause: a note about scope had been added to the end of `LICENSE`, so GitHub's license detection no longer matched the standard MIT text.

## Decision

- **Code:** the MIT License, in `LICENSE`, word for word, with no added text.
- **Writing:** Creative Commons Attribution 4.0 International (CC BY 4.0), in `LICENSE-CONTENT`, using the full legal code word for word.
- `docs/REUSING.md` explains which files each license covers, how to credit us, and what neither license covers: third-party laws, forms, and pages; the optional font (SIL Open Font License 1.1); and our name and mark.
- Contributions come in under the same licenses that the project uses (writing under CC BY 4.0, code under MIT). `CONTRIBUTING.md` says so.
- Every page's footer names both licenses. The CC BY 4.0 link uses `rel="license"`, a standard machine-readable marker.

## Sources opened on 2026-11-03

- CC BY 4.0 legal code: [creativecommons.org/licenses/by/4.0/legalcode.txt](https://creativecommons.org/licenses/by/4.0/legalcode.txt). The text in `LICENSE-CONTENT` came from GitHub's license catalog ([github/choosealicense.com](https://github.com/github/choosealicense.com), `_licenses/cc-by-4.0.txt`, commit `b054bc8`). We matched its opening and closing notices and sections 2(a)(6), 2(b)(2), and 6(a) against the Creative Commons page.
- MIT License: [SPDX license list, MIT](https://spdx.org/licenses/MIT.html). `LICENSE` matches the standard text in the same GitHub catalog (`_licenses/mit.txt`), with the year and holder filled in.
- Credit format: Creative Commons, [Recommended practices for attribution](https://wiki.creativecommons.org/wiki/Recommended_practices_for_attribution) (page last edited December 4, 2024).

## Update, 2026-11-03

The license files were renamed to match The Stasis Project ([ADR-0010](ADR-0010-shared-with-stasis.md)): `LICENSE` now holds CC BY 4.0 (the writing, which is most of the project) and `LICENSE-CODE` holds MIT. The texts did not change. Where this record says `LICENSE` for MIT or `LICENSE-CONTENT` for CC BY 4.0, read `LICENSE-CODE` and `LICENSE`.

## Consequences

- Anyone may copy, adapt, and sell copies of the guide if they follow the license: credit The Strand Project, link to the license, and say what they changed. We cannot stop an outdated copy. So `docs/REUSING.md` asks, but does not require, that copies keep each page's "last checked" date and link back.
- GitHub should list both licenses for the repository (our reading of how GitHub detects license files; not confirmed until it shows on the repository page).
- CC BY 4.0 does not license trademarks, and it gives no permission to suggest we endorse a copy (sections 2(b)(2) and 2(a)(6)). The MIT License does not mention trademarks.
