# Proposal: Bundle icons inside the Python package for wheel installs

## Why

Users who install scantpaper from a wheel (`pip install scantpaper` or a local
`scantpaper-*.whl`) see missing icons in their toolbar. `app.py` locates icons
via `os.path.join(dirname(__file__), "../icons")`, which only resolves in a
source checkout. In a wheel the package lives in `site-packages/scantpaper/`, so
`../icons` does not exist and the `/usr/share/scantpaper/icons` fallback is
unreachable for user-level pip installs. The wheel also ships no icons at all —
`[tool.setuptools.package-data]` only bundles `app.ui`. The only current real
wheel user (openSUSE, which has no package) cannot rely on a distro path, so the
wheel must become self-contained.

## What Changes

- Move the `icons/` directory from the repository root into the `scantpaper`
  package (`scantpaper/icons/`), so the icons travel with the code.
- Resolve the icon path from the installed package using
  `importlib.resources.files("scantpaper")` instead of string-joining
  `__file__` with `../`.
- Add the icons to the wheel via `[tool.setuptools.package-data]`.
- Update the `/usr/share/scantpaper/icons` fallback so distro installs (deb)
  continue to work if the packaged icons are not present.
- Update tests that reference `app.iconpath` / the `../icons` layout.

## Capabilities

### New Capabilities
- `icon-loading`: Locating and registering the application's toolbar icons with
  the GTK icon theme, so they resolve in any install mode (source tree, wheel,
  distro package).

### Modified Capabilities
<!-- No existing capability covers icon discovery or packaging. -->

## Impact

- `scantpaper/app.py` — icon path resolution in `Application.__init__`
  (`iconpath` computation and the `prepend_search_path` call).
- `pyproject.toml` — `[tool.setuptools.package-data]` gains the icons glob.
- Filesystem layout — `icons/` moves to `scantpaper/icons/`; the icons
  currently shipped in `icons/hicolor/...` move with it.
- Existing tests in `scantpaper/tests/test_app.py`,
  `scantpaper/tests/test_text_layer_control.py`, and
  `scantpaper/tests/test_app_window.py` that reference `app.iconpath` and the
  `../icons` path will be updated.
- The `.deb` packaging path (deb.yml) is checked to confirm whether it installs
  icons to a system theme independently of the moved directory.
- No new runtime dependencies (`importlib.resources` is stdlib, py3.10+).
