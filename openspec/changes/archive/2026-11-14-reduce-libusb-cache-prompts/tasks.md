# Tasks

## 1. Settings and cache-origin tracking

- [x] 1.1 Add a `warn-libusb-cache` boolean (default `True`) to
  `DEFAULT_SETTINGS` in `src/scantpaper/config.py`; verify a config test
  reports the default and that a config without the key loads the default.
- [x] 1.2 Add `_device_list_from_cache` to `ScanMenuItemMixins`, set it around
  the cached-list assignment in `scan_dialog`, and reset it in `finally`;
  verify a unit test shows a cache load is marked and a fresh path is not.

## 2. Prompt only for new lists, with suppression

- [x] 2.1 Rework `_confirm_libusb_caching` to return immediately when the list
  has no `libusb` name or `warn-libusb-cache` is false, use explicit OK/Cancel
  buttons and a single body string, and add a "Don't ask again" checkbox
  honoured only on OK; verify tests for suppression, OK with and without the
  checkbox, and cancel.
- [x] 2.2 Make `_changed_device_list_callback` store a cache-loaded list without
  asking, while still asking for new `libusb` lists when warning is enabled;
  verify a cache-load `libusb` test shows no dialog and a stored list, and that
  a following fresh `libusb` list still asks.

## 3. Documentation and translations

- [x] 3.1 Update `README.md` to explain when the `libusb` caching question
  appears, how to stop it, and how to re-enable it by editing the config;
  verify the text names the cache preference and `warn-libusb-cache`.
- [x] 3.2 Regenerate the translation template and seed fuzzy entries for the
  new and changed msgids; verify `PYTHONPATH=src python3 dev/check_po.py`
  passes.

## 4. Integration checks

- [x] 4.1 Run `pytest` and verify the full suite passes with the coverage gate;
  audit with `python3 dev/check_test_coverage.py` and confirm no new uncovered
  lines.
- [x] 4.2 Run `ruff format --check .`, `ruff check .`, and `ty check .`; verify
  all three are clean.
- [x] 4.3 Run `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`; verify both pass.

## Workflow follow-up

- Archive the change with `/opsx-archive` after review.
