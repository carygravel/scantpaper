## 1. Dependency registry module

- [x] 1.1 Create `src/scantpaper/dependencies.py` with a `ProbeResult`
      record (`version`, `using_fallback`) and a frozen `Dependency`
      dataclass (`name`, `probe`, `message`, `warn_at_startup`)
- [x] 1.2 Add a `program_version_probe(stream, regex, cmd)` factory that
      wraps `helpers.program_version` into a probe, preserving the exact
      commands and regexes currently used
- [x] 1.3 Define the registry `DEPS` covering imagemagick (with the
      graphicsmagick fallback returning `using_fallback`), graphicsmagick,
      xdg, djvu, libtiff, pdftops, pdfunite, pdf2ps, qpdf, unpaper, and
      tesseract/tesserocr, in an order that reproduces the current startup
      message ordering
- [x] 1.4 Write `src/scantpaper/tests/test_dependencies.py` covering each
      probe (present/absent/version-parse) and the registry's order and
      message fields

## 2. Rewire the window code

- [x] 2.1 Rewrite `_check_dependencies()` in `session_mixins.py` to iterate
      `DEPS`, call each probe, and store `name -> version | None` into
      `_dependencies`; keep the Tesseract engine choice and the
      GraphicsMagick compatibility warning (reacting to `using_fallback`)
- [x] 2.2 Rewrite `_missing_packages_message()` in `app_window.py` to derive
      the message from the registry, preserving exact text and ordering
- [x] 2.3 Update `unpaper.py` so `program_version()` reuses the registry
      probe while keeping its existing public signature

## 3. Tests and documentation

- [x] 3.1 Update `test_session_mixins.py` and `test_app_window.py` where
      needed; add assertions that the message text/order and the
      graphicsmagick fallback warning are unchanged
- [x] 3.2 Run `ruff format --check src/scantpaper/`, `ruff check
      src/scantpaper/` and `ty check .`
- [x] 3.3 Run the full `pytest` and confirm the 99% coverage gate passes
      with no touched file worse than before
- [x] 3.4 Confirm no translatable string was added or removed; run
      `PYTHONPATH=src python3 dev/generate_pot.py` and
      `PYTHONPATH=src python3 dev/check_po.py` (0 errors, no new advisories)
