## Why

Ubuntu 22.04 (jammy) remains a supported target until 2027-06, and Ubuntu
24.04 (noble) is the current LTS, but the GTK4 port currently passes only on
the maintainer's Debian sid toolchain. The current jammy CI log records 107
failures and 61 errors; the earlier count of 13 failures and 3 errors predated
later fixes. All of them trace to toolkit and dependency assumptions that are
newer than the supported floor. This blocks the PPA and release artifacts for
the platforms the project still promises to support.

## What Changes

- Record the supported platform floor explicitly: Python >= 3.10, GTK >= 4.6
  and PyGObject >= 3.42, with jammy supported until 2027-06 and noble
  thereafter. No runtime dependency is raised or removed.
- Rework the main-window menu definition so `app.ui` loads on GTK 4.6 through
  4.24 instead of requiring the inline-menu support added in GTK 4.17.5.
- Build `Gdk.RGBA` values by assigning components, so confidence colours are
  rendered correctly on PyGObject versions before 3.52 instead of becoming
  transparent black.
- Replace the `do_dispose` timeout cleanup with a hook that exists and runs on
  PyGObject 3.42+, so the scroll-idle timer is removed when the view is
  destroyed.
- Make the GSK test helper walk container nodes with the GTK 4.6 API, and make
  the rotated-text test recognise rotations expressed by a Form XObject
  transformation matrix, as OCRmyPDF 17.13 now emits, rather than assuming a
  page-level `Tm`.
- Load the thumbnail stylesheet with `Gtk.CssProvider.load_from_data`, because
  `load_from_string` only exists from GTK 4.12, and keep the rule inspectable
  on the oldest PyGObject.
- Commit fractional spin-button values from a `Gtk.EventControllerKey`
  instead of the `Gtk.SpinButton::activate` signal, which only exists from GTK
  4.8, so pressing Enter validates the entry on jammy.
- Keep the paint-level thumbnail assertion on PyGObject versions that can
  marshal `Gtk.Snapshot`; on 3.42, assert the installed CSS rule instead of
  calling the binding that segfaults.
- Keep the jammy (`oldest`) CI job as the compatibility gate, and document the
  support window in `README.md` and the release procedure.

## Capabilities

### New Capabilities

- `platform-compatibility`: The supported toolkit, Python and Ubuntu release
  floor, and the requirement that release artifacts stay within it.

### Modified Capabilities

- `main-menu`: The menu model must load from the shipped UI definition on every
  supported GTK 4 version, not only on GTK 4.17.5 and later.
- `canvas-widget`: Confidence colours must render as the intended opaque
  colours on every supported PyGObject version, including 3.42-3.50.

## Impact

- `src/scantpaper/app.ui`: move the menu model to a top-level object and
  reference it from `GtkPopoverMenuBar`.
- `src/scantpaper/app_window.py`: load the thumbnail stylesheet with
  `load_from_data` and return the provider for inspection.
- `src/scantpaper/canvas.py`: replace positional `Gdk.RGBA(...)` construction.
- `src/scantpaper/helpers.py`: commit fractional spin buttons from a key
  controller rather than the missing `activate` signal.
- `src/scantpaper/imageview.py`: move idle-timeout cleanup from `do_dispose` to
  a portable unrealize hook.
- `src/scantpaper/tests/`: GSK child traversal, colour expectations, dispose
  test, rotated-text assertions, thumbnail CSS/paint checks, and a shared
  spin-button Enter helper.
- `README.md` and `release_procedure.md`: state the jammy end date and the
  GTK/PyGObject floor.
- `.github/workflows/test.yml`: unchanged matrix; `oldest` continues to run on
  Ubuntu 22.04 and becomes the enforcement point.
- No dependency changes; the minimum OCRmyPDF remains 16.10.0 and the tests
  accept the 17.13 text-layer structure.
