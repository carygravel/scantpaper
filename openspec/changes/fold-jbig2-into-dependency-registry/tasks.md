## 1. Registry and availability function

- [x] 1.1 Add a cached `_jbig2_version()` and `probe_jbig2()` to
      `src/scantpaper/dependencies.py`, parsing `jbig2 --version` stderr
      with `jbig2enc\s+([\d.]+)`
- [x] 1.2 Add a `jbig2` `Dependency` to `DEPS` with `warn_at_startup=True`
      and the message "JBIG2 PDF compression requires jbig2", after `qpdf`
- [x] 1.3 Move `jbig2_available()` into `dependencies.py`, delegating to
      `_jbig2_version()`; remove it from `helpers.py`

## 2. Update consumers

- [x] 2.1 Update the `jbig2_available` import to `scantpaper.dependencies`
      in `dialog/save.py`, `dialog/preferences.py`, `savethread.py`, and
      `tests/test_1111_save_pdf.py`

## 3. Tests and documentation

- [x] 3.1 Add a `probe_jbig2` test and include `jbig2` in the
      registry-ordering test in `test_dependencies.py`
- [x] 3.2 Update `test_missing_packages_message_order` in
      `test_app_window.py` to include a `jbig2` dependency key and pin the
      jbig2 warning position
- [x] 3.3 Run `ruff format --check src/scantpaper/`, `ruff check
      src/scantpaper/` and `ty check .`
- [x] 3.4 Run the full `pytest` and confirm the 99% coverage gate passes
- [x] 3.5 Regenerate the template and run `dev/check_po.py` (0 errors); the
      new jbig2 message becomes a new fuzzy-capable msgid
