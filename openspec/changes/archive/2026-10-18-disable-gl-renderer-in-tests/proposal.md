# Proposal: disable-gl-renderer-in-tests

## Why

Since the GTK3→GTK4 migration, a full `pytest` run reproducibly segfaults in
`test_dialog_scan.py` (around `test_race_condition_device_switching`, the 28th
test in the file). The cause: GTK4 auto-selects a GL-based GSK renderer
(`ngl`/`gl`), which under pytest-xvfb's Xvfb (no DRI3) runs on Mesa's software
rasteriser (llvmpipe). Repeated GL-context create/destroy across the ~30 tests
that `present()` real windows, plus live worker threads pumping a GLib
mainloop, is a crash-prone combination. GTK3 never had a GL renderer by
default, so neither the `libEGL ... DRI3` warnings nor the segfault existed
before the migration. The renderer choice must not be left to
machine-dependent auto-selection: it makes the suite hermetic on one machine
and a lottery on another (CI runs the same GL-on-llvmpipe path on GPU-less
runners).

## What Changes

- Pin the GTK renderer for the test suite in `src/scantpaper/conftest.py`,
  before GTK initialises:
  - `GSK_RENDERER=cairo` (no GL renderer, no GL contexts).
  - `GDK_DISABLE=gl` (skips EGL/GL initialisation at display open entirely,
    which also silences the `libEGL warning: DRI3 error` noise).
  Both via `os.environ.setdefault` so a developer can still override
  explicitly.
- Bump pytest-xvfb's colour depth from the 16-bit default to 24
  (`xvfb_colordepth` ini setting in `pyproject.toml`), removing another
  legacy-GL aggravator.
- Test-only infrastructure change: no application code, no user-visible
  behaviour change.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — this change alters no application requirements, so `skip_specs: true`
is set in `.openspec.yaml`)

## Impact

- `src/scantpaper/conftest.py`: environment setup at import time.
- `pyproject.toml`: one ini setting under `[tool.pytest.ini_options]`.
- CI (`.github/workflows/test.yml`) runs plain `pytest` under xvfb and
  inherits the fix automatically; no workflow change.
- No runtime application code, dependencies, or APIs affected.
- Verification: repeated full-suite `pytest` runs on the affected machine must
  complete without segfault, and the `libEGL` DRI3 warnings must be gone.
