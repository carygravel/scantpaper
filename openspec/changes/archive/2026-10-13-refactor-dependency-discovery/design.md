## Context

See proposal.md - Why. Today `_check_dependencies()` in `session_mixins.py`
builds `window._dependencies` (`name -> version str | None`) from a mixed
`dependency_rules` table plus bespoke branches for tesseract/tesserocr
(Python libs), unpaper (its own cached `program_version()`), and an
imagemagick/graphicsmagick fallback with a side-effecting warning dialog.
`app_window.py::_missing_packages_message()` separately hardcodes the list
of dependencies and their user-facing texts. `jbig2_available()` in
`helpers.py` is a separate, lazy, `@lru_cache` check used by dialogs and the
save worker thread.

## Goals / Non-Goals

**Goals:**

- One declarative registry that is the single source of truth for what each
  dependency is, how to detect it, and its startup message.
- Derive both `_dependencies` population and `_missing_packages_message()`
  from that registry so they cannot drift.
- Preserve the exact `_dependencies` shape, the exact missing-message text
  and order, and the GraphicsMagick compatibility warning.
- Make each probe independently unit-testable.

**Non-Goals:**

- No lazy probing (YAGNI - the app already probes these eagerly at startup
  and startup cost is not a measured problem).
- No folding JBIG2 into the registry (see Decisions).
- No change to the value type stored in `_dependencies` (stays
  `name -> version | None`).

## Decisions

- **Represent each dependency as a `Dependency` frozen dataclass** with
  `name`, `probe` (a pure `Callable[[], ProbeResult]`), `message`, and
  `warn_at_startup`. `ProbeResult` is a small frozen record of `version`
  plus a `using_fallback: bool` flag (see the GraphicsMagick case). A pure
  probe keeps detection testable without a window; the window layer reacts
  to `using_fallback`.
- **Fold CLI tools into command-based probes built on `program_version`**.
  The existing `dependency_rules` tuples (name/stream/regex/cmd) map
  directly onto a factory, so most entries become one-line probe
  definitions - preserving the exact commands and regexes already in use.
- **tesseract/tesserocr and unpaper become callable probes.** tesseract
  returns `tesserocr.tesseract_version()`; unpaper reuses its version probe
  via the registry instead of a bespoke method. The current
  `_ocr_engine.append` of the Tesseract engine choice stays in
  `_check_dependencies()` (or is keyed off the stored tesseract version),
  preserving behaviour.
- **Keep the GraphicsMagick fallback and its warning, but separate
  detection from the dialog.** The imagemagick probe returns a `ProbeResult`
  whose `version` is the GM version when IM is absent and whose
  `using_fallback` is set; `_check_dependencies()` then shows the existing
  "GraphicsMagick compatibility" warning. This keeps detection pure and the
  side effect in the window layer. Alternative - keeping the fallback as
  inline post-loop logic - was rejected because it leaves detection
  heterogeneous and untestable in isolation.
- **`_missing_packages_message()` iterates the registry** in registry
  order, appending each `warn_at_startup` dependency's `message` when its
  stored version is falsy. The registry is ordered to reproduce the current
  message ordering exactly (imagemagick, libtiff, djvu, xdg, unpaper, ocr,
  qpdf). The `ocr`/tesseract row and the qpdf row keep their current text.
- **Do not fold JBIG2 in.** It is intentionally a lazy, feature-gated check
  used from dialogs and the save worker thread where no window is in scope
  (`savethread.py`), and it already has the desired `@lru_cache` behaviour.
  Folding it in would couple those call sites to the window-owned registry.
  This matches the earlier analysis that JBIG2 is a different kind of
  dependency from the eager, window-scoped startup checks.
- **Keep `_dependencies` shape unchanged** so the many mixin consumers and
  existing tests are untouched; only `_check_dependencies` and
  `_missing_packages_message` are rewritten against the registry.

## Risks / Trade-offs

- [Registry order changes the startup message] → Order the registry to
  match the current `missing` list; pin the full message in a test.
- [GraphicsMagick warning side effect complicates a pure probe] → Split
  detection (pure `ProbeResult`) from the dialog; test the probe's
  `using_fallback` flag and the dialog reaction separately.
- [Rewriting `_check_dependencies` breaks existing tests that mock it
  wholesale] → Those tests mock the method, so they keep passing; new
  registry/probe unit tests are additive. Consumers of `_dependencies`
  values are unchanged.
- [Unpaper's bespoke `program_version` diverges] → Have the registry reuse
  the same detection; keep `Unpaper.program_version` as a thin wrapper so
  existing callers are unaffected.

## Migration Plan

Pure internal refactor: no data, config, or user-visible migration. The
`_dependencies` dict and its consumers are unchanged, so nothing else needs
to change and rollback is trivial (revert the registry rewrite).
