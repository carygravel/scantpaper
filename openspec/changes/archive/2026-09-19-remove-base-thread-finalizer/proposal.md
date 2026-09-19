## Why

The `weakref.finalize` registrations that funnel into `BaseThread.cleanup_thread`
(`requests_queue.put(Request("quit", ...))`) are dead code in every reachable
state, yet they are a steady source of runtime noise. When pytest-timeout fires
its SIGALRM exactly while garbage collection is running one of these
finalizers, pytest's `Failed` (a `BaseException`) escapes the finalizer's
`except Exception` guard and surfaces as a `PytestUnraisableExceptionWarning`:
"Exception ignored on calling weakref callback". At interpreter shutdown the
same code can touch half-torn-down `queue`/`threading` internals and raise
again. Production and the test suite both quit worker threads explicitly, so
the finalizer side effect serves no reachable purpose.

## What Changes

- Remove the `weakref.finalize` registrations from `basethread.py`,
  `basedocument.py`, and `dialog/sane.py`.
- Remove the now-unused `BaseThread.cleanup_thread` static method (and the
  test that only exercises it: `testcleanup_thread_exception_caught`).
- Harden the real cleanup path: run `_release_sources()` from a `finally`
  block in `BaseThread.run()` so the GLib sources and pipe FDs are always
  released however the worker exits.
- Keep `BaseThread.LiveThreads` / `quit_all_live_threads()` as the explicit,
  GC-independent leak guard for tests and external callers.

No user-visible behaviour changes; thread lifecycle behaviour is unchanged for
the reachable paths (explicit quit in the app, `quit_all_live_threads()` in
tests). This is a pure internal refactor of worker-thread cleanup.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — no spec-level behaviour changes. Marked `skip_specs: true` in
`.openspec.yaml` because worker-thread cleanup is an implementation detail, and
the observable external behaviour (explicit quit, live-thread registry) is
unchanged.

## Impact

- `src/scantpaper/basethread.py` — drop the `weakref.finalize` registration and
  `cleanup_thread`; wrap `_release_sources()` in `try/finally` inside `run()`.
- `src/scantpaper/basedocument.py` — drop the finalizer registration
  (`self._finalizer = weakref.finalize(...)`).
- `src/scantpaper/dialog/sane.py` — drop the finalizer registration.
- `src/scantpaper/tests/test_083_basethread.py` — remove
  `testcleanup_thread_exception_caught`; add coverage for the `finally` cleanup
  path (sources/FDs released even when `run()` exits via a quit break or an
  error).
- Eliminates the intermittent `PytestUnraisableExceptionWarning` class and the
  interpreter-shutdown crash mode for worker threads. No new dependencies.