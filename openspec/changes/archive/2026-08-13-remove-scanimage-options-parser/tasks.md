## 1. Rescue live-production test coverage

- [x] 1.1 Add `within_tolerance` branch tests to `scantpaper/tests/test_scanner_options.py`, constructing minimal `Option` lists directly (range with quant exact/inexact + tolerance param, list constraint, `TYPE_BOOL`/`TYPE_STRING` equality positive/negative, `TYPE_INT`/`TYPE_FIXED` difference vs tolerance, constraint-`None` fall-through) — see design.md D2
- [x] 1.2 Run `test_scanner_options.py` and confirm the new `within_tolerance` tests pass against the current code

## 2. Remove the parser and enforce list-only construction

- [x] 2.1 In `scantpaper/scanner/options.py`, delete `_parse_scanimage_output()` and the `else` branch in `Options.__init__`; make non-list input raise `TypeError`
- [x] 2.2 Delete parser-only helpers `_parse_option()`, `parse_constraint()`, `parse_range_constraint()`, `parse_list_constraint()`, `type2value()`
- [x] 2.3 Delete parser-only constants/imports: `UNITS`, `UNIT2ENUM`, `MAX_VALUES`, `EMPTY_ARRAY`, the `SimpleNamespace` and `defaultdict` imports; remove the now-unused `Options.device` attribute
- [x] 2.4 Update the constructor error tests in `test_scanner_options.py` so `Options(None)` asserts `ValueError` and `Options("")` asserts `TypeError`

## 3. Delete parser-fidelity tests and fixtures

- [x] 3.1 Delete `test_02_scanner_options_canon.py`, `_epson1.py`, `_epson_3490.py`, `_epson_gt_2500.py`, `_hp.py`, `_brother.py`, `_snapscan.py`, `_umax.py`, `_fujitsu.py`, `_test.py`
- [x] 3.2 Delete all files under `scantpaper/tests/scanners/`

## 4. Remove orphaned methods

- [x] 4.1 Delete `delete_by_index()`, `delete_by_name()`, `by_title()` from `scanner/options.py`
- [x] 4.2 Grep the production tree for `delete_by_index|delete_by_name|by_title|_parse_scanimage_output` and confirm zero remaining references

## 5. Rename the modern from-data test

- [x] 5.1 Rename `test_02_scanner_options_from_data.py` to `test_scanner_options_from_data.py` (content unchanged)

## 6. Verification

- [x] 6.1 Run the full `pytest` suite and confirm all tests pass and coverage meets the 98% `fail-under`
- [x] 6.2 Confirm uncovered/partially-covered line counts in `scanner/options.py` are no worse than before the change
- [x] 6.3 Run `black` on changed files
- [x] 6.4 Run `pylint` and confirm the score is no worse than before; check for newly unused imports
