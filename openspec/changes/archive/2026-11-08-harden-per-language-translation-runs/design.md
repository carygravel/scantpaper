# Design

## Context

See `proposal.md` - Why. The audit already merges ledger records through
`_merge_ledger`, but the report is written from the scoped result alone, and
the ledger writer rewrites every language file. `build_report` also carries a
hard-coded notes sentence whose numbers were already stale before this change.

`deterministic_checks` compares placeholders, format fields, spaced `printf`
tokens and emptiness. `deterministic_plural_checks` reuses it per form, so a
line-structure check added there covers plural forms without a second path.

## Goals / Non-Goals

**Goals:**

- A scoped audit leaves every unselected language unchanged in both the
  report and the ledger.
- The report's totals and notes stay correct after a scoped run.
- A proposal that would fail `msgfmt --check` on newlines cannot be approved.

**Non-Goals:**

- Re-auditing every catalog on a scoped run.
- Comparing internal newlines or exact whitespace between words.
- Changing the report schema or the ledger schema.

## Decisions

### Merge the report in the auditor, not in callers

Add `merge_report(existing, result)` next to `build_report`. It replaces the
selected language blocks, pending and parked groups, then recomputes totals
and notes from the merged language map. `main` uses it only when
`--language` selected a subset; a full run still builds a fresh report.

Alternative: always re-audit every catalog and write a complete report.
Rejected because a scoped run is the common per-language workflow and a full
audit would compare all 36 catalogs on every run.

If the existing report names a different snapshot, the merge is refused and a
fresh report is written, because blocks from two snapshots cannot be averaged.

### Preserve pending order per language

The existing report lists pending entries grouped by language in a stable
order. The merge keeps that order, replaces the selected language's group in
place, and appends a newly audited language at the end in sorted order.

### Write only the audited language ledgers

After `_merge_ledger`, call `write_language_ledger` for each language in
`result.catalogs` instead of `write_ledger` for the whole directory. That
keeps unrelated files byte-identical and avoids the reordering churn.

Alternative: keep `write_ledger` and accept the reordering. Rejected because
it makes every per-language run produce thousands of no-op diff lines.

### Count leading and trailing newlines

The new check compares the number of leading newlines and the number of
trailing newlines in the source and the translation. A difference is a defect
named `leading newline changed` or `trailing newline changed`.

Alternative: only require `str.endswith("\n")` parity, as `msgfmt` does.
Rejected because two newlines versus one is still a layout change. Alternative:
compare exact whitespace prefixes and suffixes. Rejected because spaces may be
adjusted by a legitimate translation while newlines may not.

## Risks / Trade-offs

- A translation that legitimately wants to drop a trailing newline now
  abstains → the reason is explicit, and the maintainer can review and record
  a human approval.
- A scoped report merge can leave an unselected language block describing an
  older catalog → the block is only as fresh as its last audit, which is the
  same contract as today; a full run refreshes everything.
- The newline check applies to every form of a plural entry through the
  existing per-form loop → a form that loses a newline blocks the whole set,
  which is the intended behavior.

## Migration Plan

No data migration. The next audit run for any language rewrites only its own
report block and ledger. Rollback is a code revert; catalogs and approvals
keep their digests.
