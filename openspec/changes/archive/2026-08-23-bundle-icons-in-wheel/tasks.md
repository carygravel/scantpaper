## 1. Relocate icons into the package

- [x] 1.1 `git mv icons scantpaper/icons` so the icons become package data
- [x] 1.2 Confirm no code outside the package references the old `../icons`
      root path (grep for `../icons` and `icons/hicolor`)

## 2. Resolve icons from installed package resources

- [x] 2.1 In `app.py` `Application.__init__`, replace the
      `os.path.join(dirname(__file__), "../icons")` computation with
      `os.path.join(dirname(__file__), "icons")` (in-package path)
- [x] 2.2 Keep the `/usr/share/scantpaper/icons` fallback when the packaged
      path is not a directory, and retain the `prepend_search_path` call

## 3. Ship icons in the wheel

- [x] 3.1 Add the icons to `[tool.setuptools.package-data]` in `pyproject.toml`
      (e.g. `"scantpaper/icons/hicolor/*/*/*"` or an equivalent glob covering
      the SVG/PNG files)

## 4. Update distro packaging

- [x] 4.1 Update `deb.yml`'s `debian/scantpaper.install` icon line from
      `icons/* usr/share/icons/` to `scantpaper/icons/* usr/share/icons/`

## 5. Update tests

- [x] 5.1 Update tests that reference `app.iconpath` and the `../icons` path
      (`test_app.py`, `test_text_layer_control.py`, `test_app_window.py`) to
      point at the new in-package location
- [x] 5.2 Add/adjust coverage for the in-package `__file__`-based resolution
      and the system-path fallback

## 6. Verify

- [x] 6.1 Build a wheel (`python -m build` or `pip wheel .`) and confirm the
      icons are listed inside it (e.g. `unzip -l *.whl | grep icons`)
- [x] 6.2 Install the wheel into a scratch venv and confirm the GTK icon theme
      resolves the toolbar icons
- [x] 6.3 Run `pytest` — all tests pass with coverage at or above the
      configured threshold
- [x] 6.4 Run `black` and `pylint`; confirm no regressions in format or score
