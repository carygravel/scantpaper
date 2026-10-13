## Context

See proposal.md - Why. `dependencies.py` already holds the `DEPS` registry
driving both `_check_dependencies` (populating `window._dependencies`) and
`_missing_packages_message` (the startup warning). `jbig2_available()` in
`helpers.py` is the only program check left outside it. It is consumed by
`dialog/save.py`, `dialog/preferences.py`, and `savethread.py` (the save
worker thread, which has no window reference) and by integration tests.

## Goals / Non-Goals

**Goals:**

- Fold JBIG2 detection into the registry so it is probed and reported like
  the other tools.
- Add a startup warning when `jbig2` is absent.
- Keep a single probe (no duplicate `jbig2 --version` subprocess).

**Non-Goals:**

- No change to the JBIG2 feature-gating in dialogs or the save thread beyond
  the import source.
- No change to how `_missing_packages_message` is assembled (the registry
  loop already handles a new warn-at-startup entry).

## Decisions

- **Add `jbig2` as a warn-at-startup `Dependency`.** Its probe parses the
  same stderr regex (`jbig2enc\s+([\d.]+)`) from `jbig2 --version` that
  `jbig2_available` used, so detection is unchanged. The message follows the
  existing "feature requires program" pattern: "JBIG2 PDF compression
  requires jbig2".
- **Move `jbig2_available()` into `dependencies.py`**, delegating to a
  cached `_jbig2_version()` probe. This gives one source for both the
  registry's version and the feature's boolean, and the `@lru_cache` means
  the subprocess runs once even though the registry probes at startup and the
  dialogs/save thread query it later. Keeping the name `jbig2_available`
  and moving it avoids changing the consumer call sites, which continue to
  import it (just from `dependencies`). This preserves the test patches
  (`scantpaper.dialog.save.jbig2_available`, etc.) because they target the
  name in each consumer module's namespace.
- **Do not import `dependencies` from `helpers`** (that would create a cycle:
  `dependencies` already imports `program_version` from `helpers`); instead
  the function moves out of `helpers` into `dependencies`.
- **Registry ordering**: `jbig2` is appended after `qpdf`, so the startup
  warning reads ...qpdf, jbig2. This is a minor, deliberate change to the
  warning text ordering.

## Risks / Trade-offs

- [New startup warning ordering] → `jbig2` appended at the end; the
  ordering tests are updated to pin it.
- [Test fixtures that set `_dependencies` manually now need a `jbig2` key]
  → The app_window missing-message test sets `_dependencies` explicitly and
  must add `jbig2`; otherwise the registry loop KeyErrors. Updated in tasks.
- [Cross-thread read of the cached probe] → The cache is populated on the
  main thread at startup before any save runs; a later read on the worker
  thread is a read-only cache hit, which is safe.
- [Moving the import breaks tests that patch `helpers.jbig2_available`] →
  No test patches `helpers.jbig2_available`; they patch consumer-module
  names, which remain valid. `test_1111_save_pdf.py` imports the function
  directly and its import line is updated.

## Migration Plan

No data or config migration. The only user-visible change is the additional
startup warning when `jbig2` is absent; rollback is reverting the registry
entry and import moves.
