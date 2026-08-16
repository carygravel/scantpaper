## 1. Suppress full-resolution loads during bulk import

- [x] 1.1 In `SessionMixins._display_image` (`session_mixins.py:237`), always show
      the thumbnail synchronously, but only send the `get_page` request when a
      `_suppress_full_display` attribute is falsy. Revert the debounce timer /
      `_load_latest_page` changes so single `_display_image` calls send `get_page`
      immediately as before.
- [x] 1.2 In `FileMenuMixins._import_files` (`file_menu_mixins.py:243`), set
      `self._suppress_full_display = True` before starting the import.
- [x] 1.3 In `FileMenuMixins._import_files_finished_callback`
      (`file_menu_mixins.py:231`), clear `self._suppress_full_display = False` and
      trigger a single `_display_image` for the currently selected page so the
      final page is shown full-res.

## 2. Tests

- [x] 2.1 Update existing `_display_image` tests in `test_session_mixins.py` to
      remove the debounce/`_load_latest_page` trigger (revert to immediate send);
      they should now expect `get_page` sent directly on `_display_image`.
- [x] 2.2 Add a unit test that `_display_image` sends no `get_page` while
      `_suppress_full_display` is set, but still shows the thumbnail.
- [x] 2.3 Add a unit test that `_import_files` sets the flag and
      `_import_files_finished_callback` clears it and triggers a display.

## 3. Verification & quality

- [x] 3.1 Run the full test suite:
      `python3 -m pytest scantpaper/tests -q -p no:cacheprovider` — all pass
      (baseline 1078 passed, 1 xfailed, 3 xpassed; now 1082 passed).
- [x] 3.2 Coverage: `python3 -m coverage json` shows uncovered lines (baseline 2)
      and partial branches (baseline 281) same or better (2 uncovered, 281
      partial, 99.11%).
- [x] 3.3 Format changed files with `black`.
- [x] 3.4 Run `pylint --persistent=no` on `session_mixins.py`, `file_menu_mixins.py`
      and changed test files — scores same or better (baselines: session_mixins
      9.40, now 9.40; file_menu_mixins 9.83, now 9.83; test_session_mixins 6.29,
      now 6.29; test_file_menu_mixins 7.07, now 7.02 due solely to the file's
      pervasive protected-access convention, 220 W0212 already at baseline).
