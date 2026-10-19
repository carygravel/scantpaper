## 1. Active-layer state and persistence

- [x] 1.1 Add an `editmode` setting (default `"text"`) to the config defaults
  and to the recognised-setting normalisation path in `config.py`
- [x] 1.2 Seed the `editmode` action's initial state from the setting instead
  of the hardcoded `"text"` (app_window.py:299)
- [x] 1.3 Add a single internal `_set_active_layer(mode)` that applies the
  action state, both control bars' visibility, and the tabbed page or split
  canvas in one place, behind a reentrancy guard (design D2)
- [x] 1.4 Track the "last active layer" so the Image-only tab can fall back to
  it when entering split mode (design D6)
- [x] 1.5 Tests: config round-trip persists and restores `editmode`; a missing
  or malformed value falls back to `"text"`; the action is seeded from the
  setting

## 2. Fix the startup visibility mismatch

- [x] 2.1 Replace the unconditional `set_active(active=False)` pair
  (app_window.py:430-431) with applying the current active layer after the
  editors are created (design D3)
- [x] 2.2 Regression test: starting with the text layer active shows the text
  control bar on first paint, with no toggle required (the reported bug)

## 3. Keep the tab and the edit-mode selection consistent

- [x] 3.1 Move/rewire `_edit_mode_callback` onto `_set_active_layer`: select
  the matching notebook page in tabbed mode, repack the pane in split mode
- [x] 3.2 Connect the notebook `switch-page` signal to update the active layer,
  guarded against re-entry
- [x] 3.3 Implement the transition rules: tabbed Image page to split falls back
  to the last active layer; split to tabbed selects the matching page
- [x] 3.4 Tests: each transition in the `active-layer-selection` spec, plus a
  guard test that a tab change does not recurse through the action

## 4. Show the active layer's canvas in split modes

- [x] 4.1 Make `_pack_viewer_tools` pack the active layer's canvas
  (`_text_editor.canvas` or `_ann_editor.canvas`) instead of always `t_canvas`
- [x] 4.2 Make `_change_view_cb` detach the active canvas (not always
  `t_canvas`) when leaving tabbed mode
- [x] 4.3 Update `test_pack_viewer_tools*` and the `_real_layout_window` suite
  for the canvas swap
- [x] 4.4 Tests: a split view with annotations active shows the annotation
  canvas and hides the text canvas; switching the active layer swaps the pane

## 5. Documentation and quality gates

- [x] 5.1 Document the View-menu layer selection and the split-mode layer
  behaviour in README.md
- [x] 5.2 Run `ruff format` and `ruff check` clean
- [x] 5.3 Run `ty check .` with no diagnostics
- [x] 5.4 Run `pytest`; ensure coverage does not regress relative to baseline

## 6. Lay out the edit bar

- [x] 6.1 Pack the edit bar at its minimum height so the view keeps the
  remaining vertical space (design D7), with a test
