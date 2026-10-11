# Tasks: Fix split view panes collapsing on startup

## 1. Add a helper to initialise split-pane position

- [x] 1.1 Add `_init_split_pane(pane, orientation, saved_position)` to
  `app_window.py` that restores a saved position or sets a one-shot
  `size-allocate` handler applying a half-split default, then disconnects
  itself.
- [x] 1.2 Call `_init_split_pane` from the horizontal and vertical branches of
  `_pack_viewer_tools`, passing the saved config value for the active mode.

## 2. Persist the split-pane position

- [x] 2.1 Add `"split panel h": None` and `"split panel v": None` to
  `config.DEFAULTS`.
- [x] 2.2 In `_can_quit` (file_menu_mixins.py), when the active view is
  horizontal/vertical, store `_hpanei.get_position()`/`_vpanei.get_position()`
  into the matching config key alongside the existing `"thumb panel"` write.
- [x] 2.3 Confirm `write_config`/`read_config` round-trip the new keys with no
  special-casing needed.

## 3. Tests

- [x] 3.1 Extend `test_pack_viewer_tools` to assert `_init_split_pane` is
  invoked with the pane, orientation and saved position for both split modes.
- [x] 3.2 Add a test that a saved split position is passed through and a
  `None` saved position selects the half-default path.
- [x] 3.3 Add a test that `_can_quit` persists the active pane's position and
  ignores the inactive orientation.
- [x] 3.4 Add a regression test (with real GTK widgets, restoring the
  fixture's paned-method patches) proving a split view replaces the leftover
  `_vnotebook` in `_vpaned` on startup.

## 4. Quality gates

- [x] 4.1 `pytest` passes with coverage unchanged or better.
- [x] 4.2 `ruff format` and `ruff check` clean.
- [x] 4.3 `ty check .` reports no diagnostics.
- [x] 4.4 Document the fix in README.md if it is user-visible behaviour.
