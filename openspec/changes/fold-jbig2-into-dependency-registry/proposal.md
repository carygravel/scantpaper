## Why

The JBIG2 encoder is the one external program whose detection still lives
outside the dependency registry: `jbig2_available()` in `helpers.py` is a
separate lazy check, so it is not reported at startup the way other missing
tools are, and the registry is incomplete as a single source of truth.
Moving it in makes the discovery uniform and lets the app warn the user at
startup when the JBIG2 encoder is not installed.

## What Changes

- Add a `jbig2` entry to the dependency registry (`DEPS` in
  `dependencies.py`) with `warn_at_startup=True` and a user-facing message
  ("JBIG2 PDF compression requires jbig2"), so a missing encoder is listed
  in the startup missing-package warning like the other tools.
- Move the availability check out of `helpers.py` and into `dependencies.py`
  as `jbig2_available()`, delegating to the same cached probe the registry
  uses, so there is one probe and no duplicate `jbig2 --version` invocation.
- Keep the feature-gated consumers (`dialog/save.py`,
  `dialog/preferences.py`, `savethread.py`) reading `jbig2_available()`;
  only the import source changes.

## Capabilities

### New Capabilities

- `startup-dependency-warnings`: the startup warning that lists required
  programs not installed, now including the JBIG2 encoder.

### Modified Capabilities

(none)

## Impact

- `src/scantpaper/dependencies.py`: add the `jbig2` dependency and move
  `jbig2_available()` here.
- `src/scantpaper/helpers.py`: remove `jbig2_available()`.
- Import updates in `src/scantpaper/dialog/save.py`,
  `src/scantpaper/dialog/preferences.py`, `src/scantpaper/savethread.py`, and
  `src/scantpaper/tests/test_1111_save_pdf.py`.
- Tests: registry probe/ordering tests and the startup-warning tests.
- New translatable string ("JBIG2 PDF compression requires jbig2").
