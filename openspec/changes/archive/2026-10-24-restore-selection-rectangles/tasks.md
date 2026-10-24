# Tasks

## 1. Application CSS rule for the selection rectangle

- [x] 1.1 Add `_attach_selection_css()` in `app_window.py`, next to
      `_attach_thumbnail_css()`, creating a `Gtk.CssProvider` that loads a
      `.rubberband` rule via `load_from_data()` and attaches it to the
      display at `Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION`. Call it from
      `_populate_main_window()` beside the thumbnail call. Verify with a
      unit test (mirroring the thumbnail-CSS test) that the provider
      installs and `to_string()` lists the `.rubberband` rule.
- [x] 1.2 Confirm the rule load uses only floor APIs (`load_from_data`,
      `add_provider_for_display`, no `load_from_string`) so it runs on
      jammy; verify the new unit test passes under the same headless
      fixture the thumbnail test uses, and that the `oldest` (jammy) CI
      path is unchanged.

## 2. Pixel-level visibility regression tests

- [x] 2.1 Add an ImageView test that sets a selection, renders
      `_draw_func` into an offscreen surface, and asserts pixels inside
      the selection's widget bounds are painted with the `.rubberband`
      style (reuse `_render_view`/`get_pixel`); verify it fails on the
      unfixed code and passes once the rule in 1.1 is attached.
- [x] 2.2 Add an equivalent canvas test in `tests/test_7_canvas.py` that
      renders the canvas draw path with a selection and asserts painted
      pixels within the selection's widget bounds; verify it fails before
      the rule is attached and passes after.

## 3. Theming and documentation

- [x] 3.1 Add a themability test that overrides `.rubberband` at a higher
      priority and asserts the rendered selection colour changes, checked
      for both the ImageView and the canvas; verify the override test
      passes and the default-style assertions still hold without the
      override.
- [x] 3.2 Update the README FAQ "How can I change the colour of the
      selection box" to record that a default `.rubberband` style is now
      shipped and that a user's gtk.css rule still overrides it; verify
      the FAQ wording reads consistently with the shipped behaviour.

## 4. Integration checks

- [x] 4.1 Run `pytest`, `ruff check`, `ruff format --check` and
      `ty check .`; verify zero diagnostics, line-length checks pass, and
      uncovered/partially-covered line counts are unchanged.

## Workflow follow-up

- Archive the change after the project's review requirements are
  satisfied.
- Verify the archived result.
