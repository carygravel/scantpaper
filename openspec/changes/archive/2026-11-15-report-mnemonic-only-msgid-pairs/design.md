# Design

## Context

- `dev/check_po.py` already reports source-wide msgid defects once:
  case-only duplicates, concatenation fragments, doubled spaces, U+03BC
  for MICRO SIGN, and over-long msgids. That set is advisory by design,
  because none of the conditions can be corrected automatically.
- The case-only check groups msgids that collide after lower-casing; the
  mnemonic check is the same shape with a different normalisation.
- The template currently holds 68 msgids forming 34 mnemonic-only groups.

See `proposal.md` for why this matters; the requirement is in
`specs/translations/spec.md`.

## Goals / Non-Goals

**Goals:**

- Make the duplicate visible to whoever next edits a label, so no new
  pair is added unnoticed.
- Report a group, not one condition per member.
- Keep the check consistent with the existing source-wide reports.

**Non-Goals:**

- No change to any msgid, catalog or widget.
- No judgement about marker position: the specification still forbids
  comparing a translation's accelerator with its source.
- No automatic collapse of the 34 existing groups.

## Decisions

**Normalise by removing every underscore before grouping.** A group is
the set of msgids that collapse to the same text once mnemonic markers
are removed, so `Cu_t`/`Cut`, `Zoom _in`/`Zoom in` and `Prefere_nces`/
`Preferences` are found as well as `Copy`/`_Copy`.

- Why: markers sit anywhere in this catalog. A rule that only looks at a
  leading underscore would miss 11 of the 34 groups, and those are the
  ones hardest to spot by eye.
- Alternative rejected: compare only leading markers, which keeps the
  report shorter but leaves the mid-word pairs invisible.
- Trade-off: a pair differing by a genuinely literal underscore (for
  instance an identifier and a word) would also group. The report names
  both members, so a human can dismiss it.

**Report as advisory, never as an error.** The check prints with the
other source-wide advisories and validation still exits successfully.

- Why: resolving a group means choosing which msgid survives, which can
  change which widget carries an accelerator. That is a wording decision
  for a person, like every other condition in that report.
- Boundary with "Keyboard accelerator mismatches are not checked": that
  requirement forbids comparing a translation's mnemonic with its
  source. This check compares source msgids with each other and never
  opens a catalog, so both hold. A scenario states the boundary
  explicitly.
- Alternative rejected: make it an error and clean the 34 groups in the
  same change. That forces a wording decision into a mechanical pass and
  would rewrite msgids, which turns every affected translation fuzzy.

**One line per group in the existing format.** The line lists every
member, so the reader sees the whole decision at once.

- Consequence: up to 34 extra lines on a full run. Accepted: the set is
  fixed until a msgid changes, and collapsing several groups into a
  count would hide the names the reader needs.

## Risks / Trade-offs

**The advisory output grows by up to 34 lines on every run** ->
accepted. It is one-time authoring debt and becomes shorter only when
the msgids do.

**A literal underscore pair is reported as a false positive** ->
mitigation: advisory only, and the line names both msgids so the reader
can dismiss it.

**The check could be read as reviving the accelerator check the
specification rules out** -> mitigation: the requirement names source
msgids as its input and a scenario pins that no catalog is inspected.

## Open Questions

Whether to collapse any of the 34 groups, and which of the two msgids to
keep, is left to a follow-up change. The report does not depend on the
answer, and collapsing a msgid changes catalogs, so it is not part of
this one.
