## 1. Record the compatibility floor

- [x] 1.1 Add the supported-platform statement to `README.md`: jammy and noble
  are supported, jammy until 2027-06, with Python 3.10, GTK 4.6 and PyGObject
  3.42 as the floor.
- [x] 1.2 Extend the "When jammy is dropped" section of `release_procedure.md`
  with the same floor and end date, and state that newer toolkit APIs need a
  runtime check plus fallback until that date.
- [x] 1.3 Confirm the `oldest` CI job still runs on `ubuntu-22.04` and the
  `latest`/`latest_w_ppa` jobs on `ubuntu-latest` (noble); do not add a new
  matrix entry.

## 2. Make the menu definition portable

- [x] 2.1 Move the menu in `src/scantpaper/app.ui` to a top-level `<menu>`
  object with an id, and point `GtkPopoverMenuBar` at it with a `menu-model`
  property instead of an inline menu.
- [x] 2.2 Keep every top-level label and action link unchanged; verify the
  five labels and the `win.new` link with the existing `test_app_ui` checks.
- [x] 2.3 Load `app.ui` in the GTK 4.6.9 container and confirm there is no
  `GtkBuilder` error and the menu model has five items.

## 3. Make colour construction portable

- [x] 3.1 Add an `rgba(red, green, blue, alpha=1.0)` helper to
  `src/scantpaper/canvas.py` that assigns each `Gdk.RGBA` field explicitly.
- [x] 3.2 Use the helper for both `hsv2rgb` return paths and remove every
  positional `Gdk.RGBA(...)` call from source and tests.
- [x] 3.3 Update `test_7_canvas.py` to build input and expected colours with
  the helper, and add assertions that a fully saturated red result is
  `(1.0, 0.0, 0.0, 1.0)` and that grey results stay opaque.
- [x] 3.4 Run the colour tests in the PyGObject 3.42.1 and 3.48.2 containers
  and confirm the alpha is `1.0`, not `0.0`.

## 4. Make idle-timeout cleanup portable

- [x] 4.1 Replace `ImageView.do_dispose` with `do_unrealize` in
  `src/scantpaper/imageview.py`, remove the source idempotently, and chain up
  to `Gtk.Widget.do_unrealize`.
- [x] 4.2 Guard `_scroll_idle` so it returns `GLib.SOURCE_REMOVE` without
  touching a view that no longer has a root.
- [x] 4.3 Update the scroll-timeout test to exercise the unrealize hook and
  assert the source is removed, then run it on PyGObject 3.42.1 and 3.58.0.

## 5. Update test-suite portability

- [x] 5.1 Change the thumbnail test's GSK traversal helper to use
  `get_n_children()` and `get_child(index)`; keep the same painted-size
  assertions.
- [x] 5.2 Add a rotated-text helper in `test_1111_save_pdf.py` that collects
  the page content and recursive Form XObject streams, and treats a rotated
  `Tm` or a rotated `cm` in a text-bearing stream as a rotated text layer.
- [x] 5.3 Keep the horizontal-control and `pdftotext` assertions unchanged,
  and run the rotated-text test against both OCRmyPDF 17.10 and 17.13.

## 6. Load thumbnail CSS through a floor API

- [x] 6.1 Replace `Gtk.CssProvider.load_from_string` with `load_from_data` in
  `_attach_thumbnail_css`, and return the provider so tests can inspect it.
- [x] 6.2 Assert the installed `-gtk-icon-size` rule from
  `provider.to_string()` on PyGObject 3.42.1 and 3.48.2, and keep the
  no-display guard covered.
- [x] 6.3 Keep the render-tree painted-size assertion on PyGObject >= 3.46;
  skip that test on 3.42 because `Gtk.Widget.snapshot_child` corrupts
  `Gtk.Snapshot` and segfaults, and cover the render-node walk and wait helper
  without constructing a snapshot.

## 7. Commit fractional spin values without `activate`

- [x] 7.1 Replace `widget.connect("activate", ...)` in
  `configure_fractional_spinbutton` with a `Gtk.EventControllerKey` in the
  capture phase that handles Return and KP_Enter.
- [x] 7.2 Add `emit_spinbutton_enter` to the test helpers and route the
  preferences, unpaper and scan-dialog spin tests through it.
- [x] 7.3 Run the fractional spin tests on PyGObject 3.42.1 and 3.48.2 and
  confirm the value is committed.

## 8. Verify the full matrix

- [x] 8.1 Run `pytest` locally and confirm the same or fewer uncovered and
  partially covered lines than before the change (1752 passed, 99.39%).
- [x] 8.2 Run `ruff check .`, `ruff format --check .` and `ty check .` with no
  diagnostics.
- [x] 8.3 Run the full suite on Ubuntu 22.04 (GTK 4.6.9/PyGObject 3.42.1) and
  Ubuntu 24.04 (GTK 4.14.5/PyGObject 3.48.2) and confirm zero failures and
  zero errors (jammy 1746 passed, 99.24%; noble 1748 passed, 99.29%).
- [x] 8.4 Confirm the `oldest`, `latest` and `latest_w_ppa` CI jobs are green
  before requesting review (oldest green; latest and latest_w_ppa were green
  before the PPA outage, and the PPA job cannot be re-run meanwhile).

## 9. Close test-helper coverage gaps

- [x] 9.1 Cover Form XObject traversal for non-dictionary resources, non-stream
  values, non-Form streams and repeated references, plus unrotated content.
- [x] 9.2 Assert the hOCR bbox is present instead of branching on a missing
  match, and cover a non-dictionary CCITT `DecodeParms` entry.
- [x] 9.3 Split the thumbnail stylesheet/pixbuf checks from the snapshot test
  and cover `_texture_nodes` and `_wait_for` directly or with mocks.
- [x] 9.4 Re-run the two test modules on jammy and noble; the only remaining
  misses are the skipped JBIG2 tests (no encoder in those containers) and the
  PyGObject 3.42 snapshot helper that cannot safely run at the floor.
