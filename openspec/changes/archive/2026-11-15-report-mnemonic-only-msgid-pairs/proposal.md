# Proposal

## Why

The catalog currently carries 68 msgids that form 34 pairs differing only
in where a keyboard mnemonic sits: `Copy` and `_Copy`, `Cu_t` and `Cut`,
`Zoom _in` and `Zoom in`. A translator has no way to tell which of a
pair needs a mnemonic and which does not, and the German `Delete` entry
that produced the reported `_Löschen` was authored against exactly that
ambiguity. Nothing in the validation pipeline reports the pairs, so every
new one is invisible.

## What Changes

- Report once over the source msgid set each group of msgids that become
  identical when keyboard-mnemonic markers are removed, naming every
  member of the group. There are 34 such groups today.
- Report the condition as advisory, not as an error, so validation still
  exits successfully: a duplicate msgid is a wording decision for a human,
  like the existing case-only duplicate report, and cannot be corrected
  automatically.
- Keep the report distinct from the accelerator check the specification
  rules out. That requirement forbids judging where a translation puts a
  mnemonic relative to the source; this one reports that the source
  carries the same visible word twice under two msgids.
- Cover the new condition with tests beside the existing source-wide
  msgid checks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `translations`: the set of source-wide msgid defects reported once
  gains mnemonic-only duplicates.

## Impact

- `dev/check_po.py`: one more advisory line per group, up to 34 on a full
  run, printed with the existing source-wide advisories.
- `src/scantpaper/tests/test_po_files.py`: scenario coverage for the new
  condition.
- No catalog change and no msgid change: five of the affected msgids
  already carry a mnemonic in 47 shipped translations that the new report
  only names.
- No change to validation's exit status, so CI behaviour other than the
  longer advisory output is unchanged.
