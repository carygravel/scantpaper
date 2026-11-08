# Proposal

## Why

The German catalog still has a fuzzy plural entry because the batch treats every
`msgid_plural` as unsupported. The ledger, catalog and compiler already support
plural approvals, so the only gap is the gate's proposal, checking, judging and
apply path. Without plural support, counted UI strings stay untranslated or need
an untracked manual edit.

## What Changes

- Select plural entries for a batch when the catalog header declares
  `nplurals` and the entry has the matching number of plural forms.
- Ask each proposer for the complete set of plural forms in one structured
  response, indexed by CLDR form number.
- Run the deterministic checks against every form, and reject a proposal when
  any form fails.
- Judge whole form sets rather than loose strings, and treat identical form
  tuples as the existing tie.
- Back-translate each sentence form and reject the set when any form changes
  meaning.
- Apply an approved decision to `msgstr_plural`, leaving `msgstr` empty, and
  keep the existing fuzzy-flag and ledger behaviour.
- Normalize plural form keys to strings when building an approval record.
- Estimate plural output from the declared form count so the budget stays
  accurate.
- Keep entries with `msgctxt` unsupported; add plural form-count mismatches to
  the unsupported report.
- Document the plural workflow in `po/README.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: plural entries become batch-eligible and are
  approved as a complete form set; the unsupported-entry requirement no longer
  skips plurals.

## Impact

- `dev/translation_gate.py`: batch selection, plural prompt and parser,
  deterministic checks, blind judge, back-translation, apply, report and cost
  estimate.
- `dev/translation_ledger.py`: `make_record` stores string plural keys.
- `dev/check_po.py`: reuse the existing `plural_forms_nplurals` header parser
  for the gate, or move it to a shared helper.
- Tests: `dev/tests/test_translation_gate.py`,
  `dev/tests/test_translation_ledger.py`.
- Docs: `po/README.md`.
