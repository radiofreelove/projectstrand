# ADR-0009: The mark, a strand of two twisted fibers

- Status: accepted
- Date: 2026-11-03

## Context

The first beta's mark was one white strand with a gold bead at each end. The maintainer asked for a small update. Two problems also turned up while testing it: the white strand vanished when a page was printed (white on white paper), and in a light Windows high contrast theme.

## Decision

- Keep the same line and the same gold beads. The strand is now two fibers twisted together, like the two plies of a cord: one white, one willamette green (`#86C679`, from our existing palette).
- Where one fiber passes in front of the other, the fiber behind has a small gap on each side. In the header, the gap is a mask, not a painted color, so it works on any background. The favicon sits on its own indigo square, so its gaps are painted indigo.
- `scripts/make_mark.py` draws the mark from a few numbers: the center line, the number of crossings, the spacing, and the fiber width. It writes `templates/brand-mark.svg` (the header) and `static/favicon.svg` (the browser tab). `--check` reports whether the files match the script.
- The artwork is original to this project. It is not traced from or based on another organization's mark.
- The mark stays decorative: `aria-hidden="true"`, with the site name as the link text.
- Colors: the white fiber uses the header text color, the green fiber has its own color token (`--brand-thread`), and the beads use the gold of the current-page underline. `tests/contrast.py` checks both against every header background at 3:1, the level WCAG uses for graphics. WCAG does not require this for a decorative mark; we check it anyway.
- In print, the mark turns black, green, and gold. In Windows high contrast, it takes the system text color.

## Consequences

- The header mark adds about 4 KB to each page before compression.
- To change the mark, edit the numbers in `scripts/make_mark.py` and run it. Hand edits to the two SVG files would be lost the next time the script runs.
