# Tasks

## 1. Line-structure check

- [x] 1.1 Compare the leading and trailing newline runs in
  `deterministic_checks` and return `leading newline changed` or
  `trailing newline changed` on a mismatch; verify with unit tests for a
  dropped trailing newline, an added leading newline and a preserved pair.
- [x] 1.2 Verify a plural form that loses a newline blocks the whole set
  through `deterministic_plural_checks`, and that a preserved set still
  passes.
- [x] 1.3 Verify a gate proposal that would fail `msgfmt --check` on a
  trailing newline now abstains instead of being approved.

## 2. Scoped report merge

- [x] 2.1 Add a report merge that replaces the selected language's block,
  pending entries and parked entries, preserves the other languages and their
  pending order, and recomputes the totals; verify with a unit test that an
  unselected language is unchanged and the totals match the blocks.
- [x] 2.2 Compute the report notes from the merged totals, in both the full
  and the merged path; verify a test asserts the notes quote the current
  totals rather than a fixed sentence.
- [x] 2.3 Refuse the merge when the existing report names a different
  snapshot, and write a fresh report instead; verify with a unit test.

## 3. Scoped ledger writes

- [x] 3.1 Write only the audited languages' ledger files after merging the
  records; verify that an unrelated language file is byte for byte identical
  while the selected file gains its records.

## 4. Command and documentation

- [x] 4.1 Route the audit command through the report merge when `--language`
  is given and through the full report otherwise; verify the command keeps
  every unselected language in the report.
- [x] 4.2 Document the scoped-audit behavior in the human-core section of
  `po/README.md`; verify the documented command matches the implementation.

## 5. Integration

- [x] 5.1 Run the real scoped audit for `es` against the committed report and
  verify the report still lists every language, the `es` block is unchanged,
  no other ledger file is modified, and `dev/check_po.py` and the audit tests
  pass.

## Workflow follow-up

- Archive the change once the review requirements are satisfied.
- Finish the next catalog with the scoped audit command.
