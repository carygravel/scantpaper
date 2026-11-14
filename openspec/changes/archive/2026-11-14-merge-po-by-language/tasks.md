# Tasks

## 1. Selection and validation

- [x] 1.1 Add `select_catalogs(src, languages)` to `dev/merge_po.py`: map
  stems to sorted, deduplicated `*.po` paths and raise `MergeError` with the
  unknown values and available language names; verify
  `dev/tests/test_merge_po.py` covers a named selection, a duplicate name and
  an unknown name.
- [x] 1.2 Add the repeatable `--language` option to the CLI and validate the
  selection before `write_template()`; verify `python3 dev/merge_po.py --help`
  lists the option and a test shows an unknown language leaves the template
  and every catalog byte-identical.
- [x] 1.3 Document the scoped invocation in the "Refresh the catalogs" section
  of `po/README.md`, use it in the "Translating missing entries" example, state
  that the template is still refreshed, and correct the claim that new entries
  are seeded fuzzy; verify the documented commands match
  `python3 dev/merge_po.py --help`.

## 2. Merge and reporting

- [x] 2.1 Route `merge_catalogs()` and `main()` through the selected paths
  while leaving `merge_catalog()` unchanged; verify the default still merges
  every catalog and a named selection leaves every other catalog
  byte-identical.
- [x] 2.2 Add tests proving that a scoped merge produces the same catalog bytes
  as the unscoped merge and that a filtered second run changes nothing.
- [x] 2.3 Print selected and changed catalog counts from `main()`; verify with
  `capsys` that a filtered run reports
  `N of M selected catalog(s) changed` and still names the changed stems.

## 3. Integration verification

- [x] 3.1 Run `pytest dev/tests/test_merge_po.py` and
  `python3 dev/check_po.py`; both pass and the catalog checks report 0 errors.
- [x] 3.2 Run `ruff format --check dev/merge_po.py
  dev/tests/test_merge_po.py`, `ruff check` and `ty check .`; all report no
  changes or diagnostics.
- [x] 3.3 Run `python3 dev/check_test_coverage.py` after a complete `pytest`
  run; no new uncovered or partially covered statements.
- [x] 3.4 Run `openspec validate merge-po-by-language --strict
  --no-interactive` and `openspec validate --specs --strict
  --no-interactive`; both pass.

## Workflow follow-up

- Archive the change after review and confirm
  `openspec validate --archived --no-interactive` passes.
