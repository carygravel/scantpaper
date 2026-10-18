# Design: disable-gl-renderer-in-tests

## Context

The GTK4 migration (e4e067a2) introduced GTK4's renderer auto-selection. Under
pytest-xvfb's Xvfb there is no DRI3, so EGL falls back to Mesa's software
rasteriser, and GTK4's GL renderer (`ngl`/`gl`) runs on llvmpipe. Verified by
inspection of `/proc/self/maps` in a probe process: presenting one window
loads `libEGL_nvidia`, `libgallium`, `libvulkan_lvp`, `libepoxy`; the
`libEGL warning: DRI3 error` lines are emitted by the EGL probe at
display-open time, independently of the chosen GSK renderer. The suite then
segfaults reproducibly in `test_dialog_scan.py` (`test_race_condition_device_switching`
is the 28th test; 27 dots precede the crash). `GSK_RENDERER=cairo pytest -q`
was verified on the affected machine to complete without segfault; a probe
with `GDK_DISABLE=gl` additionally produced no `libEGL` warnings and loaded no
GL libraries. GTK3 had no GL renderer by default, which is why this class of
failure post-dates the migration.

Constraint: the suite must stay hermetic and identical across developer
machines and CI (`.github/workflows/test.yml` runs plain `pytest` under xvfb
on GPU-less Ubuntu runners — currently exposed to the same lottery).

## Goals / Non-Goals

**Goals:**

- Make a full `pytest` run deterministic and segfault-free regardless of
  available GPU/EGL/DRI3 stack.
- Remove the `libEGL warning: DRI3 error` noise from test output.
- Apply to every invocation path (`pytest`, `python3 -m pytest`, CI) without
  requiring anyone to remember an env var.

**Non-Goals:**

- Fixing the ~85 GTK3-era deprecation warnings, or the
  `g_value_get_int: assertion 'G_VALUE_HOLDS_INT' failed` assertion
  (separate cleanups).
- Diagnosing the exact instruction-level fault inside Mesa/llvmpipe — the
  crash is in third-party native stacks; avoidance is the pragmatic fix.
- Exercising GTK's GL renderers in this suite. Nothing in the app requires a
  GL renderer in tests (no `GtkGLArea`; `test_thumbnail_display` asserts on
  render-node trees built by `GtkSnapshot`, which are renderer-independent).

## Decisions

- **Set both `GSK_RENDERER=cairo` and `GDK_DISABLE=gl`.**
  `GSK_RENDERER=cairo` is the long-established knob (valid across GTK 4.x)
  and alone was verified to prevent the segfault. `GDK_DISABLE=gl` stops GDK
  from initialising EGL at display open at all, which is what removes the
  `libEGL` warnings and keeps GL libraries out of the process entirely.
  Belt and braces: if a future GTK release changes one knob's semantics, the
  other still pins the suite off the GL path.
  Alternative considered: only `GSK_RENDERER=cairo` — rejected because the
  warnings (and EGL probing) would remain.

- **Set them in `src/scantpaper/conftest.py` with `os.environ.setdefault`,
  at the top of the module, before the `gi` import.** pytest imports conftest
  before test modules (and before pytest-xvfb opens the display), so every
  test-run entrypoint inherits it. `setdefault` rather than assignment so a
  developer debugging renderer-specific behaviour can still override with
  `GSK_RENDERER=ngl pytest ...`.
  Alternatives considered: `pytest-env` plugin in `pyproject.toml` — rejected
  (new dependency for one line); export in the CI workflow — rejected (does
  not fix local runs); `--no-xvfb` plus an offscreen GDK backend — rejected
  (heavier, replaces working Xvfb infrastructure).

- **Bump `xvfb_colordepth` to 24 via `pyproject.toml`
  `[tool.pytest.ini_options]`.** pytest-xvfb's default is 16 bpp, an
  under-exercised legacy visual configuration that only adds variables
  (and matters more if GL ever sneaks back in). One line, no downside for
  cairo.

## Risks / Trade-offs

- [A future test needs real GL (e.g. `GtkGLArea`)] → It would fail visibly
  under the cairo renderer; the fix is a targeted override in that test, not
  reverting the suite-wide pin. No such test exists today.
- [`GDK_DISABLE=gl` semantics differ on some GTK 4.x] → Unknown values make
  GTK abort loudly at first display open, so a mismatch fails fast and
  obviously in CI, not silently. Verified on GTK 4.24 (this machine) and the
  CI image ships 4.14, where the variable exists.
- [The segfault's exact native cause is never fully diagnosed] → Accepted
  trade-off: the crash is inside Mesa/llvmpipe, and renderer avoidance is
  deterministic and verifiable (repeat full-suite runs must pass).

## Migration Plan

Test-only change; no deployment or rollback concerns beyond reverting the two
files. Verification is the migration plan: run plain `pytest` several times
consecutively on the affected machine (and let CI run it); all runs must pass
with no `libEGL` warnings in the output.

## Open Questions

None.
