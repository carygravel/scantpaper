# Design — cancel-progress-jobs

## Context

See `proposal.md` — Why. Both halves of cancellation exist but don't connect:

- `Progress.queued()`'s cancel closure (progress.py:70-79) only calls `self.hide()`; the real `slist.cancel([pid])` is commented out and uses a stale API.
- `Document.cancel()` (basedocument.py:155) drains the request/response queues, sets `thread.cancel = True` (consumed by `check_cancelled()` breakpoints), kills pids keyed on `thread.running_pids`, then sends a `"cancel"` request (`do_cancel` resets the flag).
- `thread.running_pids` is initialized `[]` in `Importhread.__init__` and **never populated** in non-test code, so the kill loop is dead.
- Pidfiles exist per request (`create_pidfile` → `exec_command(cmd, pidfile)` writes the spawn pid) but are anonymous, **write-only** text files: `slurp(pidfile)` in `cancel()` would fail even on a populated registry.
- Only `exec_command` calls write pidfiles; many long-running children (`tiffcp`, `ddjvu`, `djvused`, `pdfimages`, `pdftotext`, `qpdf`, unpaper, post-save hooks) go through `subprocess.run`/`check_output` and are not killable at all.
- `ResponseTypes` already contains `CANCELLED` (unused); `Response` has a commented-out `pid` field; `do_cancel` resets the cooperative flag. The thread-side cancel semantics are otherwise coherent.

## Goals / Non-Goals

**Goals:**
- Cancel on a progress bar genuinely cancels the reported work and hides the bar.
- Long-running child subprocesses are terminated, not just interrupted between steps.
- `running_pids` becomes a real, live registry; `Document.cancel()`'s kill loop becomes effective.
- The app stays usable after a cancel (subsequent saves/imports work) — see `background-job-cancellation` spec.
- The W0511 FIXMEs (file_menu_mixins.py:245, basedocument.py:157) are resolved or reworded accurately.

**Non-Goals:**
- Scan-device cancellation (SANE) — already implemented via the device handle.
- Undoing/removing pages imported before a cancel — the spec fixes them as remaining.
- A visible "Cancelling…" state or progress-bar UX redesign.
- Cancelling already-finished work (e.g. post-save hooks started before `Cancel` lands).

## Decisions

### D1: Reuse the pidfile/killpg architecture, don't replace it
Keep `create_pidfile()` + `exec_command(cmd, pidfile)` + `os.killpg(os.getpgid(pid), SIGKILL)` as the kill mechanism.

- *Why:* the scaffold, tests (`test_cancel`, which asserts killpg with a pid read from a pidfile), and call-site plumbing (`kwargs["pidfile"]` threaded through every save/import path) already exist. Replacing it with a `Popen`-handle registry would touch every subprocess site and change `exec_command`'s contract for a marginal win.
- *Alternative considered:* a registry of live `Popen` objects held by the thread. Cleaner reads but a larger diff and no existing test coverage to anchor on.

### D2: Make pidfiles readable and read the pid back in `cancel()`
`TemporaryFile(mode="wt")` is write-only, so the registry cannot be a set of paths (anonymous files have no usable path) and `slurp()` can't read them.

- Open pidfiles with `mode="w+t"` in `create_pidfile()`.
- `exec_command()` calls `pidfile.flush()` after writing the spawn pid.
- Change `running_pids` to a `dict` (initialized in `Importhread.__init__`), keyed by pidfile object; register the pidfile when created, deregister when its request finishes.
- `Document.cancel()` reads each pid via `pidfile.seek(0); pidfile.read()` instead of `slurp()`.

- *Why:* no new plumbing across call sites — the pidfile object already travels in `request.args`; only the open mode, a flush, the registry type, and the read in `cancel()` change.
- *Why a dict keyed by pidfile over a list of paths:* anonymous `TemporaryFile` objects have no filesystem path to key on; keying on the object retains the write→read handoff.
- *Why `dict` over the current `[]`:* `cancel()` already does `del running_pids[pidfile]`; tests already mock it as a dict. `Importhread.__init__` initialising `[]` is a latent bug.

### D3: Register/deregister pidfiles around request execution in the thread
`pending` registration belongs with `create_pidfile()` (trivial, has `self.thread`), and cleanup belongs at request completion (the thread's `handler_wrapper` post-step), so stale entries never accumulate and the kill loop stays bounded.

- *Why a request may write multiple pidfiles:* handlers like `_do_import_pdf` spawn several sequential children and share one pidfile; registering at our creation point and cleaning at completion keeps exactly one entry live per in-flight request.
- *Race note:* the registry entry is created before any child spawns, so `cancel()` may briefly see an empty pid. It must treat an empty/unreadable pid as "skip, rely on the cooperative `cancel` flag at the next `check_cancelled()`", which `check_cancelled()` already provides.

### D4: Route remaining `subprocess.run`/`check_output` children through the pidfile path
Convert the long-running child launches in `importthread`, `savethread`, `docthread` (tiffcp, ddjvu, djvused, pdfimages, pdftotext, qpdf, unpaper, post-save hook) to go through `exec_command`-style launching with the request pidfile, preserving `check=True`/error semantics at each site.

- *Why:* a single child (e.g. `pdfimages` on a large PDF, `djvm` merge, `qpdf`) can run for a long time; the cooperative flag is only checked between children. Without D4 the "terminate subprocess" requirement cannot be met for these paths.
- *Alternative considered:* leaving them and widening `check_cancelled()` — insufficient; the flag is only sampled at breakpoints.
- *Constraint:* keep per-site behavior (exit codes, stderr surfacing via `request.error`) identical; each conversion is test-guarded (import/save integration tests exist).

### D5: Give `Progress` an owner-supplied cancel callback
`Progress` is a dumb widget; it must not reach into `slist`. Add an optional `cancel_callback` attribute set by `app_window` (`self.post_process_progress.cancel_callback = lambda: self.slist.cancel(self._cancel_finished, ...)`). The `queued()` closure then calls it (followed by the existing `self.hide()`) instead of carrying dead code.

- *Why decouple:* keeps `Progress` testable in isolation (tests assert the closure invokes the callback, not that it knows about documents), and matches how `app_window` already owns both the widget and `slist`.
- *Why `queued()` and not a one-off connect in `app_window`:* `queued()` re-connects the closure per process to pick up fresh `num_completed`/`total`; the existing `finish()` already disconnects `self._signal`.
- *Stale API:* the commented `# slist.cancel([pid])` predates the 2024 `cancel(cancel_callback, process_callback)` signature; the callback API must be used.

## Risks / Trade-offs

- **Killing a process group may take down unrelated children** (e.g. a user-defined tool spawning grandchildren) → Mitigation: keep the existing `pid == 1` guard; scope killpg to the spawned child's group; document that hook commands may be terminated.
- **Empty-pid race at cancel time** (registry entry created before spawn) → Mitigation: skip empty pids; the cooperative `cancel` flag stops the job at its next `check_cancelled()`.
- **Converting `subprocess.run` sites can change error behavior** (`check=True` raising vs Proc return codes) → Mitigation: preserve semantics per site; rely on the import/save integration tests, including the `test_cancel_*` cases.
- **Post-save hooks already running when Cancel lands** continue to completion (D4 kills children only while their owning request is active; a hook is its own spawn) → Accepted: matches the spec's "no partially-written output presented as completed" (output was written before the hook) and is better than killing user scripts mid-flight.
- **Cross-thread use of a shared `TextIOWrapper`** (main thread reads pid while worker is blocked in `communicate()`) → Mitigation: worker writes once and flushes, then blocks in `communicate()` without touching the file; the read is a single seek/read of a tiny file. Acceptable and testable.

## Migration Plan

Internal-only change; no data migration, no config, no dependencies. Rollback is reverting the change. Deploy order: thread/pidfile plumbing (D2, D3) → subprocess routing (D4) → GUI wiring (D5) → spec-covering tests. Tests assert no behavioral regression for save/import paths.

## Open Questions

- Should a cancelled progress bar briefly show "Cancelling…" so the user sees ack of the click before the bar hides? Deferrable UI nicety; not required by the specs. Default: hide immediately.