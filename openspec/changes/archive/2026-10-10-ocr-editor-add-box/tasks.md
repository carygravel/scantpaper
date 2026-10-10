# Tasks

## 1. Expose and gate the Add button

- [x] 1.1 Store the Add button as an attribute on `LayerControls` (e.g.
      `self.add_button`) instead of a local, so its state can be controlled.
- [x] 1.2 Add a method to `LayerControls` to set the Add button's enabled
      state and switch its tooltip between "Add text" and a "draw or select a
      rectangle first" message.
- [x] 1.3 In `LayerEditor`, connect to the view's `notify::selection` and
      update the Add button state: enabled when a selection exists, disabled
      otherwise.
- [x] 1.4 Add unit tests in `test_layer.py` covering: disabled Add with no
      selection, enabled Add with a selection, and the disabled tooltip.

## 2. Draw a selection rectangle in the layer panes

- [x] 2.1 Add a selection overlay property to `Canvas` so it renders the
      current selection rectangle (mirroring the view's selection).
- [x] 2.2 Bind the canvas selection to the view's `selection` property, using
      the existing `bind_property` pattern for `zoom`/`offset` in
      `session_mixins.py`.
- [x] 2.3 Implement left-drag rectangle drawing on the canvas over empty space
      (no existing box hit), showing a live rectangle that becomes the
      selection on release; keep left-click-to-focus and middle-drag panning.
- [x] 2.4 On release, convert the drawn rectangle to image coordinates and
      commit it to the view via `view.set_selection`, so the single shared
      selection is updated.
- [x] 2.5 Add unit tests in `test_7_canvas.py` and `test_imageview.py` for:
      drawing a rectangle in a layer pane, click still focusing an existing
      box, and the selection appearing on the image view.

## 3. Wire the shared selection end to end

- [x] 3.1 Verify both the text and annotation editors reflect the shared
      selection and both Add buttons track it (no selection in either pane
      disables both).
- [x] 3.2 Confirm the Add control, using a layer-pane-drawn selection, inserts
      a slice at that rectangle (matching the existing "Slices can be added
      and duplicated" scenario) for both an existing layer and a fresh layer.

## 4. Integration and quality gates

- [x] 4.1 Update README.md for the user-visible change (draw a box in the
      layer pane; Add is disabled until a rectangle is drawn/selected).
- [x] 4.2 Run the full test suite (`pytest`) and confirm coverage thresholds
      are met or improved.
- [x] 4.3 Run `ruff format` and `ruff check` with no errors.
- [x] 4.4 Run `ty check .` with no diagnostics.
