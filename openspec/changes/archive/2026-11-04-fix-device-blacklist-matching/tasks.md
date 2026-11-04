# Tasks

## 1. Correct the matcher

- [x] 1.1 Extract the filtering loop into a pure helper that returns a new
  list and treats the blacklist as the pattern, then add unit tests where
  the pattern differs from the device name; verify the new tests fail on
  the old argument order and pass with `pytest
  src/scantpaper/tests/test_scan_menu_item_mixins.py`.
- [x] 1.2 Match the helper against a newline-joined haystack of label,
  name, vendor, and model with `re.IGNORECASE | re.MULTILINE`; verify tests
  cover a label match, a backend-name match, a non-match, and a pattern
  containing spaces.
- [x] 1.3 Add a compatibility test proving that an exact backend-name
  blacklist still omits the device; verify it passes alongside the other
  matcher tests.
- [x] 1.4 Update the existing `_changed_device_list_callback` blacklist
  test so its pattern cannot match under both argument orders; verify
  `pytest src/scantpaper/tests/test_scan_menu_item_mixins.py` passes and a
  temporary reversion of the argument order makes it fail.

## 2. Guard empty results and the cached path

- [x] 2.1 Handle an empty filtered list in `_changed_device_list_callback`
  by reporting "No devices found" and never indexing `device_list[0]`;
  verify a test with every device blacklisted passes without an
  `IndexError`.
- [x] 2.2 Apply the same filter when `scan_dialog` installs a cached
  device list, leaving command-line `--device` lists untouched; verify
  tests show a cached blacklisted entry omitted without a rescan.
- [x] 2.3 Add a cached-list test where every entry is blacklisted; verify
  the no-devices outcome is reported and no exception escapes.

## 3. Add the one-click blacklist action

- [x] 3.1 Add a `blacklist-device` signal and a button beside the Device
  combo, sensitive only for a real selected device; verify dialog tests
  cover the emitted payload and the disabled state for the rescan row and
  `NO_INDEX`.
- [x] 3.2 Handle the signal in the mixin by appending
  `re.escape(label)` with `|`, skipping an entry already present,
  refreshing the selector, and persisting the setting; verify tests cover
  the appended value, escaping, duplicate suppression, and list refresh.
- [x] 3.3 Add a test showing that blacklisting a second device leaves the
  existing blacklist entry intact; verify it passes with the action tests
  in `pytest src/scantpaper/tests/test_scan_menu_item_mixins.py`.

## 4. Hints, documentation, and translations

- [x] 4.1 Update the blacklist tooltip and add an entry placeholder that
  name the matched label/name fields and give an example; verify the
  preferences dialog test asserts both strings.
- [x] 4.2 Document the device blacklist behaviour and the new action in
  `README.md`; verify the described workflow matches the implemented
  controls.
- [x] 4.3 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py` and run
  `PYTHONPATH=src python3 dev/check_po.py`; verify the catalog checks pass
  with no new translations added.

## 5. Integration verification

- [x] 5.1 Run `pytest`, `ruff format --check`, `ruff check`, and
  `ty check .`; verify all pass with no new suppressions.
- [x] 5.2 Run `python3 dev/check_test_coverage.py` after a complete pytest
  run; verify the uncovered and partial line counts match or improve on
  the baseline.
- [x] 5.3 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate fix-device-blacklist-matching --no-interactive`;
  verify both report no errors.

## Workflow follow-up

- Archive the change after review and a successful implementation run.
