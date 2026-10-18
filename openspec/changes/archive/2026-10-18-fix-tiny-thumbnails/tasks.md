## 1. CSS fix

- [x] 1.1 Add a `thumbnail-list` CSS class to the document list widget in
  `BaseDocument.__init__` (src/scantpaper/basedocument.py).
- [x] 1.2 Load a `Gtk.CssProvider` at application startup with the rule
  `.thumbnail-list.image { -gtk-icon-size: <THUMBNAIL>px; }`, where the pixel
  value is interpolated from the `THUMBNAIL` constant, and attach it to the
  default display with `STYLE_PROVIDER_PRIORITY_APPLICATION`.

## 2. Regression test

- [x] 2.1 Add a paint-level test: import a page into a real `Document`,
  snapshot the thumbnail list widget under `pytest-xvfb`, and assert the
  painted thumbnail matches the generated pixbuf size (allowing for panel-edge
  clipping).
- [x] 2.2 Confirm the new test fails without the CSS fix (e.g. by skipping the
  provider locally) and passes with it.

## 3. Verification

- [x] 3.1 Run `pytest` with no coverage regression versus the baseline.
- [x] 3.2 Run `ruff format`/`ruff check` and `ty check .` clean.
- [x] 3.3 Run the app under Xvfb with an imported page and visually confirm
  the thumbnail paints at the generated size; note the result in README.md if
  user-visible behaviour is worth mentioning (it is a bugfix, so likely just
  the changelog).
