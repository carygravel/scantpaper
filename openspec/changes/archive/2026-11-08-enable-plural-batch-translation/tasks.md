# Tasks

## 1. Plural selection and prompting

- [x] 1.1 Add a shared plural-form-count reader and make
  `_select_batch_entries` select a plural entry when the catalog header
  declares `nplurals` and `msgstr_plural` has that many forms; report a
  missing header or a count mismatch as unsupported. Verify with tests that a
  valid two-form entry, a valid three-form entry and a malformed entry are
  classified correctly.
- [x] 1.2 Add a plural prompt builder that includes both source forms, the
  declared form count and the catalog's `plural=` expression, plus a strict
  parser into a form-index mapping. Verify tests cover two and three forms,
  a wrong count, a missing index, a duplicate index and extra prose.
- [x] 1.3 Update `estimate_gate` to include `msgid_plural` and scale expected
  output by the declared form count. Verify the estimate test shows a larger
  high bound than the same source treated as singular.

## 2. Plural evidence

- [x] 2.1 Run `deterministic_checks` once per form against the source form set
  and fail a proposal when any form fails. Verify tests cover a placeholder
  change in form 1, an empty form and a format-field change.
- [x] 2.2 Present each proposal to the blind judge as a complete ordered form
  set and compare full form tuples for the identical-proposal tie. Verify
  tests cover a judged set, an identical set that skips the judge, and a set
  where only one form differs.
- [x] 2.3 Back-translate every sentence form and block the set when any form
  changes meaning. Verify tests cover one passing set and one set with a bad
  second form.

## 3. Apply, record and document

- [x] 3.1 Extend `_entry_for` and `make_record` for plural sources and
  normalize `msgstr_plural` keys to strings. Verify the ledger accepts the
  record and rejects an equivalent record with a wrong digest.
- [x] 3.2 Make `_apply_decision` write `entry.msgstr_plural`, leave
  `entry.msgstr` empty and reject an incomplete form set. Verify a catalog
  round trip through `compile_mo` renders every form.
- [x] 3.3 Include the approved form set in the batch summary and JSON report.
  Verify the CLI report names the forms for a plural approval.
- [x] 3.4 Document plural batch translation and the form-count requirement in
  `po/README.md`. Verify the documented command matches the implemented CLI.

## 4. Integration

- [x] 4.1 Add an end-to-end fake-client test that selects, gates, applies and
  validates a two-form and a three-form plural entry, including one
  abstention. Verify the catalog, ledger and report agree.
- [x] 4.2 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_po.py` and
  `openspec validate enable-plural-batch-translation --strict --no-interactive`.
  Verify all pass with no new uncovered lines.
