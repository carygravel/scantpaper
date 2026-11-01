# Tasks

## 1. Tool mode plumbing

- [x] 1.1 Give the `Selector`, `Dragger` and `SelectorDragger` classes a
  `mode` attribute holding their `const.py` identifier, and add a
  `tool_mode` string property to `ImageView` that `set_tool` updates.
  Verify in `test_imageview.py` that each tool reports its constant and
  that `set_tool` changes the property.
- [x] 1.2 Add a `tool_mode` string property to `Canvas`, defaulting to
  `SELECTORDRAGGER_TOOL`. Verify in `test_7_canvas.py` that a bare canvas
  reports the default and accepts a new value.
- [x] 1.3 Bind `ImageView.tool_mode` to both canvases in
  `_add_text_view_layers` with `GObject.BindingFlags.DEFAULT |
  GObject.BindingFlags.SYNC_CREATE`. Verify in `test_session_mixins.py`
  that both canvases copy the view's initial mode and follow a later
  `set_tool`.

## 2. Image view button policy

- [x] 2.1 Add `Tool.handles_button`, returning `False` in the base class,
  primary-only for `Selector` and `Dragger`, and primary-or-middle for
  `SelectorDragger`; gate `ImageView._button_pressed` and
  `_button_released` on it. Verify in `test_imageview.py` that a middle
  press is ignored by Select and Pan, accepted by Select & Pan, and that
  an ignored middle release does not end a running gesture.
- [x] 2.2 Reject non-primary buttons in `Selector.button_pressed` as
  defence in depth. Verify with a direct middle-button call that it
  returns `False` and starts no selection.
- [x] 2.3 Verify that `SelectorDragger` still selects with the primary
  button and pans with a middle drag after the gate, extending
  `test_selector_dragger_tool` with a motion and offset assertion.

## 3. Canvas routing and feedback

- [x] 3.1 Extract the existing middle-button pan into `_begin_pan`,
  `_pan_to` and `_end_pan`. Verify the existing canvas pan tests, such as
  `test_drag_text_layer`, still pass unchanged.
- [x] 3.2 Route `_button_pressed`, `_motion` and `_button_released` by
  `tool_mode`: primary pans under Pan, primary selects or focuses under
  the selecting tools, middle pans only under Select & Pan, middle is
  inert otherwise, and the secondary button stays inert. Verify with a
  table-driven test covering all three modes and both primary and middle
  buttons, plus a secondary press, asserting offset movement and whether
  `selection-drawn` fires.
- [x] 3.3 Commit the gesture at press, so changing `tool_mode` between
  press and release does not switch an in-progress drag between panning
  and selecting. Verify by changing the mode mid-drag and asserting the
  started gesture completes.
- [x] 3.4 Keep word focus to the selecting modes. Verify that under Pan a
  primary press on a word focuses nothing and pans on drag, while the
  existing Select and Select & Pan focus tests still pass.
- [x] 3.5 Add a canvas `_update_cursor` showing `grab`/`grabbing` in the
  Pan mode, `crosshair` in the selecting modes, and clearing off the
  page; call it from motion, press and release. Verify with
  `Gdk.Cursor.new_from_name` mocks that the expected names are requested
  and the cursor is cleared off the page.
- [x] 3.6 Update README's View Menu matrix and the layer-editing
  paragraph so the tool scope covers both viewers and the middle button
  is documented per tool. Verify by re-reading both sections against the
  specs.
- [x] 3.7 Add an entry under 4.0.3 (unreleased) in `changelog.md` for the
  canvas following the tool and the restricted middle button. Verify the
  entry matches the README wording and the shipped behaviour.

## 4. Integration verification

- [x] 4.1 Run `pytest` from the repository root and confirm the full
  suite passes.
- [x] 4.2 Run `ruff format --check .` and `ruff check .` and confirm both
  are clean.
- [x] 4.3 Run `ty check .` and confirm it reports no diagnostics.
- [x] 4.4 Run `python3 dev/check_test_coverage.py` and confirm no new
  uncovered or partially covered lines beyond the recorded baseline
  (type-only imports under `TYPE_CHECKING` excepted).
- [x] 4.5 Run `openspec validate canvas-follows-image-tool --strict` and
  confirm the change validates.

## Workflow follow-up

- Smoke-test the app interactively: in a split view switch to Pan and
  drag both panes, switch to Select and drag, then switch to Select & Pan
  and middle-drag. This is a manual check, not a tracked task.
- Archive the change after review with
  `openspec archive canvas-follows-image-tool`.
- Verify the archived `canvas-widget` and `image-view-tools` specs kept
  the full modified requirement blocks and their scenarios.
