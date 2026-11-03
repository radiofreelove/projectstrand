# Review checklist

Copy this into every pull request that changes content. The pull request template includes it.

## Sources

- [ ] I opened and read every source I cited, on the date I put in `checked`.
- [ ] New sources are in `data/sources.yml` with the right `status`.
- [ ] Changed numbers live in `data/facts.yml`, not in page text.
- [ ] For any law, I checked for newer session laws, effective dates, and bills.
- [ ] Anything I could not confirm is labeled "Not confirmed"; any interpretation is labeled "Our reading."
- [ ] The research memo in `docs/research/` is updated, including its research log.

## Words

- [ ] The answer comes first ("The big picture").
- [ ] `python3 tests/readability.py` shows grade 8 or lower for the pages I changed, and I shortened any new long sentences.
- [ ] New legal terms are defined on the page and in the word list.
- [ ] No legal advice: I described the process and did not tell anyone what to choose.
- [ ] No personal case details anywhere.

## Build and checks

- [ ] `python3 build.py` passes with no new warnings.
- [ ] `python3 tests/check_site.py`, `tests/contrast.py`, and `tests/browser_checks.py` pass.
- [ ] I tried the changed page with a keyboard only and on a phone-sized screen.

## Records

- [ ] I updated the page's `checked` date in `data/pages.yml` if I re-checked it.
- [ ] I added an entry to `docs/AUDIT-LOG.md`.
- [ ] I added a line to `CHANGELOG.md` if readers would notice the change.
