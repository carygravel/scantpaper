# Proposal

## Why

Finishing the remaining catalogs one language at a time exposed two tooling
defects that force manual repair on every run:

- `dev/audit_human_core.py --language <lang> --apply` replaces
  `po/translation-audit.json` with a report containing only the selected
  language, and rewrites every language's ledger in a new order. The Spanish
  run had to restore the report from git and merge the block through the API,
  and three unrelated ledgers had to be reverted as pure reordering churn.
- `deterministic_checks` does not compare leading or trailing newlines, so
  the gate approved two Spanish translations that dropped a trailing `\n`.
  Only `msgfmt --check` caught them afterwards, and fixing them required
  re-digesting both approval records.

Both defects will recur for every catalog still to finish, and the second one
can ship a layout defect if a release skips the later check.

## What Changes

- A scoped human-core audit merges the audited language into the existing
  report: its language block, its pending entries, and the recomputed totals
  and notes. Unselected languages are preserved byte for byte.
- A scoped audit writes only the audited languages' ledger files, so an
  unrelated language's ledger is not reordered.
- The report notes are computed from the merged totals instead of a stale
  hard-coded sentence.
- The deterministic checks reject a translation whose leading or trailing
  newline run differs from the source, so a translation that would fail
  `msgfmt --check` cannot be approved.
- Tests cover the scoped report merge, the ledger isolation and the newline
  check, including the exact two Spanish defects.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: the deterministic checks gain a line-structure
  requirement, and the human-core audit gains an explicit whole-report
  requirement for scoped runs.

## Impact

- `dev/audit_human_core.py`: report merge, note generation and per-language
  ledger writes.
- `dev/translation_gate.py`: leading and trailing newline check in
  `deterministic_checks`.
- Tests: `dev/tests/test_audit_human_core.py`,
  `dev/tests/test_translation_gate.py`.
- No catalog or ledger data migration. The next report refresh replaces the
  current one, and existing approvals keep their digests.
