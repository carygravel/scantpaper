## Why

The `test_02_scanner_options_*` tests and the `_parse_scanimage_output()` machinery in `scanner/options.py` are leftovers from the gscan2pdf era, when the app obtained scan options by calling `scanimage --help` and parsing the text output. The app now talks to scanners exclusively through python-sane, which returns option descriptors as tuples. In production the parser branch of `Options.__init__` is never reached — it is dead code kept alive only by its own tests.

## What Changes

- Remove the dead scanimage/scanadf text parser from `scanner/options.py`:
  - `_parse_scanimage_output()`, `_parse_option()`, `parse_constraint()`, `parse_range_constraint()`, `parse_list_constraint()`, `type2value()`
  - Parser-only constants and imports: `UNITS`, `UNIT2ENUM`, `MAX_VALUES`, `EMPTY_ARRAY`, `SimpleNamespace`, `defaultdict`
  - The `Options.device` attribute (populated only by the parser, read only by parser tests)
- Remove the orphaned methods with no production callers: `delete_by_index()`, `delete_by_name()`, `by_title()`
- **BREAKING (internal)**: `Options.__init__` now raises `TypeError` for any non-list input (ruff `TRY004`). Previously a string fell through to the parser branch (empty string silently produced an empty options array).
- Delete the parser-fidelity tests and their fixtures:
  - `test_02_scanner_options_canon.py`, `_epson1.py`, `_epson_3490.py`, `_epson_gt_2500.py`, `_hp.py`, `_brother.py`, `_snapscan.py`, `_umax.py` (pure parser checks)
  - All 16 files in `scantpaper/tests/scanners/`
- Rescue and relocate the tests that exercise live production logic:
  - `within_tolerance()` coverage (only current source) and the constructor error tests from `test_02_scanner_options_test.py` move to `test_scanner_options.py`, built directly from `Option` lists instead of parsed text
  - `test_02_scanner_options_from_data.py` (already drives the list branch) is renamed to `test_scanner_options_from_data.py` to drop the legacy `test_02_` prefix

## Capabilities

No spec-level behavior changes. This is a pure refactor (removal of dead code and test reorganization) — `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- **`scantpaper/scanner/options.py`**: shrinks by roughly 250 lines; `Options` now accepts only a list of option descriptors.
- **`scantpaper/dialog/scan.py`**: unaffected (imports `Options, within_tolerance`; `within_tolerance` survives).
- **`scantpaper/dialog/sane.py`**, **`scantpaper/dialog/pagecontrols.py`**: unaffected — both pass lists to `Options`.
- **Tests**: 9 parser-fidelity test files and 16 fixture files deleted; `test_scanner_options.py` gains the rescued tests; `test_02_scanner_options_from_data.py` renamed.
- **Coverage**: parser branches currently contributing partial-coverage warnings disappear; the 98% `fail-under` must be re-verified after the change.
