## Why

External-program discovery is split across two places that can drift:
detection rules live in `_check_dependencies()` (`session_mixins.py`) as a
heterogeneous mix of a data table, Python-lib checks, and bespoke branches,
while the startup "missing package" message is a separate hardcoded list in
`app_window.py`. Adding or changing a dependency means editing two places,
and the special cases (tesseract, unpaper, the imagemagick/graphicsmagick
fallback) each follow a different shape. There is no single, uniform,
testable source of truth for "what does this program require and how do I
detect it".

## What Changes

- Introduce a declarative dependency registry: one `Dependency` record per
  external program, each carrying its name, a pure detection probe (a
  callable returning the version or `None`), its user-facing "missing
  package" message, and whether it is warned about at startup.
- `_check_dependencies()` becomes a uniform loop over the registry that
  stores `name -> version | None` into `_dependencies`; the bespoke
  branches (tesseract/tesserocr, unpaper, xdg/djvu/libtiff/etc.) are folded
  into probes.
- The imagemagick/graphicsmagick fallback becomes part of the imagemagick
  probe, which returns a result carrying a "using GM fallback" flag;
  `_check_dependencies()` still shows the existing GraphicsMagick
  compatibility warning when that flag is set, preserving current behavior.
- `_missing_packages_message()` in `app_window.py` is derived from the
  registry: for each `warn_at_startup` dependency whose version is falsy,
  append its message. Message text and ordering are preserved exactly.
- The `_dependencies` dict shape (`name -> version | None`) is unchanged,
  so every mixin consumer and existing test is unaffected.
- The JBIG2 check is deliberately **not** folded in: it is a lazy,
  feature-gated, worker-thread check that is already decoupled (see design),
  and stays as `jbig2_available()`.

No user-visible behaviour changes. This is a pure refactor (hence
`skip_specs: true` in `.openspec.yaml`).

## Capabilities

### New Capabilities

(none - pure refactor, `skip_specs: true`)

### Modified Capabilities

(none - no spec-level behaviour change)

## Impact

- New module `src/scantpaper/dependencies.py`: the `Dependency` record, the
  registry, and the probe helpers (reusing `program_version` from
  `helpers.py`).
- `src/scantpaper/session_mixins.py`: `_check_dependencies()` rewritten to
  iterate the registry; the GraphicsMagick warning moved to react to the
  probe's fallback flag.
- `src/scantpaper/app_window.py`: `_missing_packages_message()` derived from
  the registry.
- `src/scantpaper/unpaper.py`: `program_version()` may reuse a registry
  probe instead of its own bespoke method.
- Tests: registry/probe unit tests in a new `test_dependencies.py`, plus
  updates to `test_session_mixins.py` and `test_app_window.py` that today
  mock `_check_dependencies` wholesale.
- No dependency, packaging, or translation changes.
