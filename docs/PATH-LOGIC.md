# How the path finder works

The path finder lives in [`templates/pages/path.html.j2`](../templates/pages/path.html.j2) and [`static/js/path.js`](../static/js/path.js). This page describes every question, every block of steps, and which lines each answer shows, so anyone can audit it without reading code. The Stasis Project keeps the same kind of note for its 1-minute check ([checker-logic.md](https://github.com/radiofreelove/projectstasis/blob/main/docs/checker-logic.md)).

## Promises

- **Answers stay on the page.** They live in page memory only. They are never saved, even when "Remember" is on ([PRIVACY.md](PRIVACY.md)). The Content Security Policy sets `connect-src 'none'` and `form-action 'none'`, so the browser blocks any attempt to send them.
- **Steps, not outcomes.** The tool shows which offices, forms, and fees apply. It never says whether a court or agency will say yes.
- **Every line names its source.** Each line carries a source tag, and the page lists its sources like every other page. Lines we could not confirm, or had to interpret, carry the same "Not confirmed" and "Our reading" labels the state pages use.
- **Works without the tool.** With JavaScript off, the page links to the state, federal, after-court, and compare pages, which hold every step the tool can show.

## The questions

| # | Question | Answers |
|---|---|---|
| 1 | Where do you live? | Oregon; Washington; Utah; Somewhere else |
| 2 | What do you want to change? | Name; Gender marker (legal sex); Both |
| 3 | Who is this for? | Me, 18 or older; My child (I am a parent or guardian); Me, under 18 |
| 4 | Where were you (or your child) born? | Oregon; Washington; Utah; Another U.S. state or territory; Outside the United States |

All 4 must be answered. If any is missing, the tool lists the missing questions by name and moves focus to the first one. "Start over" clears the answers and the results.

## How the steps are chosen

1. The tool shows up to six blocks, always in this order:
   1. **Court**, by where you live
   2. **Social Security and passports**, for everyone
   3. **Driver license or ID**, by where you live
   4. **Birth certificate**, by where you were born
   5. **After that**, for everyone
   6. **Help**, by where you live
2. Inside a block, a line can be marked for certain changes (name, marker, both) or certain people (adult, parent, minor). A marked line shows only if your answers match. An unmarked line shows for everyone.
3. Empty lists are removed. A block with nothing left is skipped. Every block today keeps at least one line or link for every set of answers, so all six show.
4. Blocks are numbered "Step 1," "Step 2," and so on, in the order shown.
5. A summary sentence repeats your answers, for example: "These steps are for a name change for yourself, when you live in Oregon, with a Washington birth certificate."

**"Both" shows everything "Name" or "Gender marker" would show.** The one exception is Oregon court: one petition covers both changes, so "Both" gets its own line instead of the name line and the marker line. [`tests/path_rules.py`](../tests/path_rules.py) checks this rule for all 180 answer combinations on every build.

## Which lines show

"Everyone" means every answer to questions 2 and 3.

### Court

| Block | Line, in short | Shows for |
|---|---|---|
| Oregon | Name change petition in your county; fee or waiver; name-only cases are public | Adult, name |
| Oregon | You may not need court for a marker change; if you do, any circuit court; confidential | Adult, marker |
| Oregon | One petition for both at any circuit court; confidential | Adult, both |
| Oregon | Parent or guardian files the minor forms; where to file; notice to the other parent | Parent, any change |
| Oregon | Under 18, a parent, guardian, or legal representative files unless you are emancipated | Minor, any change |
| Washington | Public case at district court or sealed case at superior court; every name change has a hearing | Name or both, anyone |
| Washington | No court needed for the marker on a Washington license or birth certificate; an order is optional | Marker or both, anyone |
| Washington | Parent or guardian can file a child's name change, sealed if it relates to gender identity | Parent, any change |
| Washington | Talk with a parent, guardian, or legal aid; the minor birth certificate form needs a parent and a provider | Minor, any change |
| Utah | District court in the county where you lived at least a year; hearing; fee or waiver | Adult, name or both |
| Utah | Sex designation: clear and convincing evidence of six things; papers private, hearings public | Adult, marker or both |
| Utah | No sex designation change under 15 years and 6 months, or without the custodial parent's permission; takes effect at 16 | Parent or minor, marker or both |
| Utah | Child's name change: district court in the county where the child has lived for a year; other parent consents or is served; hearing | Parent or minor, name or both |
| Somewhere else | Use your state court's self-help pages or legal aid; Lambda Legal's help desk | Everyone |

### Social Security and passports (everyone)

| Line, in short | Shows for |
|---|---|
| Ask Social Security for a replacement card after your name legally changes | Name or both |
| Social Security is not changing sex markers right now | Marker or both |
| Passports show the sex assigned at birth, and X is not offered | Everyone |

### Driver license or ID

These lines do not change with question 3, so a parent asking for a young child also sees them.

| Block | Line, in short | Shows for |
|---|---|---|
| Oregon | Choose M, F, or X at the DMV; no proof; in person; fee | Marker or both |
| Oregon | Change your name with Social Security first | Name or both |
| Washington | Choose M, F, or X in person or by mail with form 520043; free for the marker alone | Marker or both |
| Washington | Bring your certified court order to the Department of Licensing after Social Security | Name or both |
| Utah | Bring legal documentation; sealed court documents accepted | Name or both |
| Utah | We could not confirm how Utah changes the sex on a license (labeled "Not confirmed") | Marker or both |
| Somewhere else | Check your state's DMV; many ask you to update Social Security first (labeled "Our reading") | Everyone |

### Birth certificate

| Block | Line, in short | Shows for |
|---|---|---|
| Oregon | Form OHA 2673, notarized, for name, sex, or both; no court; M, F, or X; once each | Everyone |
| Oregon | For someone under 18, a parent or legal guardian applies | Parent or minor |
| Oregon | Or send a certified court judgment; other states' orders accepted | Everyone |
| Oregon | Cost | Everyone |
| Washington | Sex designation by Department of Health form, not court; M, F, or X; fees | Marker or both |
| Washington | Adults use DOH 422-143, notarized | Adult, marker or both |
| Washington | Minors use DOH 422-144, with a parent or guardian and a licensed provider | Parent or minor, marker or both |
| Washington | Name: certified court order with DOH 422-126 | Name or both |
| Utah | Court order, form 902, and fee to Utah Vital Records | Everyone |
| Utah | New certificate does not show what changed unless you ask | Marker or both |
| Another U.S. state | Only your birth state can change it; find its office | Everyone |
| Outside the U.S. | A U.S. court or office cannot change it; talk with an immigration lawyer first if you have U.S. immigration documents (labeled "Our reading") | Everyone |

### After that, and Help

"After that" links everyone to the after-court checklist. "Help" shows the help for the state where you live, or Lambda Legal's help desk for somewhere else, and links to the full help page.

## Known limits

- The tool covers only Oregon, Washington, and Utah courts and offices. "Somewhere else" gets general pointers and the federal steps.
- It does not ask about a person's own situation beyond the 4 questions (for example, emancipation, custody, or a sealed record). Lines that depend on those say so in words.
- The Driver license or ID lines are the same for adults and children.

## Changing the rules

1. Edit the line in `templates/pages/path.html.j2`, keeping its source tag.
2. Update the matching row on this page.
3. Run `python3 tests/path_rules.py` and the browser checks (`tests/browser_checks.py`).
4. Record the change in [AUDIT-LOG.md](AUDIT-LOG.md).
