## Context

See proposal.md — Why: the `weakref.finalize` registrations feeding
`BaseThread.cleanup_thread` are dead code in every reachable state, yet they
run arbitrary code (a `queue.Queue.put`) from the two contexts least safe for
it: a garbage-collection finalizer and interpreter shutdown.

Current state (shapes the approach):

- Three registrations funnel into the same queue put:
  - `basethread.py:131` — finalizer on the thread object itself.
  - `basedocument.py:54` — finalizer on the document.
  - `dialog/sane.py:49` — finalizer on the scan dialog.
- The thread-self finalizer cannot fire while the worker runs: `BaseThread`
  overrides `run()` (`basethread.py:260`), no subclass overrides it again, and
  the `run()` frame holds `self`, pinning the object until the worker exits.
  By the time that finalizer fires, `_release_sources()` has already run and
  the queued quit is never consumed.
- The owner-level finalizers are redundant: production quits both threads
  explicitly on close (`file_menu_mixins.py:966,975`) and holds exactly one
  document (`app_window.py:359`), and the test suite quits every live thread
  after each test (`conftest.py:54-58`).
- The reported warning (see trigger analysis in the conversation) fired when
  pytest-timeout's SIGALRM landed in the thread-self finalizer mid-GC; pytest's
  `Failed` derives from `BaseException`, so `cleanup_thread`'s `except
  Exception` guard (intended to swallow everything) did not catch it.

## Goals / Non-Goals

**Goals:**

- Eliminate every `weakref.finalize` side effect on worker-thread lifecycle so
  no code runs inside a GC finalizer.
- Guarantee GLib sources (io watch + 200 ms tick) and the pipe FDs are released
  however the worker exits.
- Keep the explicit, GC-independent leak guards (`LiveThreads` +
  `quit_all_live_threads()`).
- Preserve observable behaviour exactly: ownership, request lifecycle, and
  progress reporting are untouched.

**Non-Goals:**

- Changing how requests, callbacks, or progress reporting work.
- Adding a timed `requests.get(timeout=...)` polling loop to wake workers off a
  plain "dead" flag (considered, rejected — see Decisions).
- Fixing the pre-existing deferral of `_release_sources()` when a worker exits
  while no GLib main loop is running (out of scope; unchanged by this change).

## Decisions

**1. Remove the finalizers entirely rather than patching `cleanup_thread`.**
Alternatives considered:

- Broaden `except Exception` to `except BaseException` (option B). Catches the
  reported signal case but keeps running arbitrary code in a GC finalizer and
  inside mostly-torn-down interpreter state; every future body edit re-opens
  the trap.
- Gate on `sys.is_finalizing()` (option C). Only helps the shutdown case;
  the reported warning happened mid-suite during GC, where the gate is `False`,
  so it would not have fixed the observed failure at all.
- Remove now, accept the loss of a never-reachable backstop. Chosen: the
  backstop (owner finalizer stopping a dropped live worker) is unreachable in
  production (single document, single scan window, both explicitly quit) and
  redundant in tests (`quit_all_live_threads`).

**2. Release worker resources from a `finally` block in `run()`.**
The worker's only real cleanup point is `_release_sources()` (removes GLib
sources, closes FDs). Today it is the last statement of `run()`, so any exit
path that skips it leaks for the process lifetime. Wrapping it in
`try/finally` makes cleanup unconditional for quits, handler errors, or
unexpected exceptions.

**3. Keep `LiveThreads` / `quit_all_live_threads()` as the sole leak guard.**
Because the worker pins its own object via the `run()` frame, a dropped owner
with a live worker still leaves the thread visible in the `WeakSet`, so the
existing teardown/fixture can stop it. No new notification mechanism is needed.

**4. Delete `cleanup_thread` and its lone test.**
With the three registrations gone, `cleanup_thread` has no callers;
`testcleanup_thread_exception_caught` (`test_083_basethread.py:473`) only
freezes the outdated swallow-exceptions contract and is removed with it.

## Risks / Trade-offs

- [Dropped un-quit document leaks its worker (daemon thread, GLib sources,
  FDs, SQLite connection)] → No reachable path drops a live document or scan
  window without quitting; tests use the autouse `quit_lingering_threads`
  fixture as backstop. Mitigation: a test asserting `quit_all_live_threads()`
  still stops an un-quit worker.
- [`finally` in `run()` masks the point where an unexpected exception escapes]
  → The worker-loop exceptions are already routed via `handler_wrapper`; the
  `finally` only touches cleanup, and `_release_sources()` swallows
  `OSError` on already-closed FDs.
- [`_release_sources()`'s idle callback still defers to the next main-loop
  iteration if the worker exits with no loop active] → Pre-existing and
  unchanged; eventually every worker exit happens around a main-loop
  iteration, which drains it.

## Migration Plan

Internal refactor, no data or config migration. Single atomic change; rollback
is a revert of the implementing commit.

## Open Questions

None. Decisions that could have changed the approach (B vs removal, polling
loop vs finalizer) were resolved above because they determine the task
breakdown.