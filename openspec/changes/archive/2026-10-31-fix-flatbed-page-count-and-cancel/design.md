# Design

## Context

See `proposal.md` for motivation. The current scan chain is:

```text
scan_pages(num_pages)
  -> scan_page
       -> do_scan_page (start + snap)
       -> _scan_pages_finished_callback
            -> import page
            -> if page limit reached or feeder empty: cancel + finish
            -> else: scan_page again
```

`num_pages == 0` means "All". On a flatbed there is no feeder-empty status,
so only a page limit or a cancel ends the chain. `SaneThread.cancel()` is
used both for a user cancel and for the natural end of a batch, and it
drains queued requests, sets `_cancel_requested`, queues a `cancel`
request, and calls `device_handle.cancel()` from the GTK thread as a
best-effort unblock.

The dialog guard is in `_changed_scan_option_callback`: it forces one page
on a flatbed only when `allow_batch_flatbed` is false. When the preference
is true, the ADF default `All` is inherited. The `num_pages` setter accepts
a non-1 value on a flatbed whenever `allow_batch_flatbed` is true.

Two further constraints shape the approach. `flatbed_selected()` performs a
synchronous `get_option_value()` on the GTK thread with a 10 s timeout, and
its `suppress(AttributeError)` does not catch a timeout or a backend
exception. The progress bar's Cancel handler is reconnected on every
`started-process` event and is not disconnected on normal completion.

## Goals / Non-Goals

**Goals:**

- Make the flatbed page-count default safe and explicit, independent of the
  ADF default and of saved profiles.
- Make a user cancel invalidate the batch so a pending completion cannot
  queue another page.
- Keep the application responsive and recoverable when a backend ignores a
  cross-thread cancel.
- Keep the ADF default and feeder behaviour unchanged.
- Test all of this without scanner hardware.

**Non-Goals:**

- Changing `python-sane` or the `_sane` C extension's blocking `snap()` read
  loop. A cancel-aware read loop is a possible upstream improvement, not
  part of this change.
- Replacing the `scan_pages` callback chain with `_SaneIterator`.
- Changing which non-scan requests `cancel()` drains.
- Changing the `allow-batch-flatbed` key, default, or migration. The
  preference still permits multi-page flatbed batches; it no longer implies
  an unbounded batch.
- Resetting a USB device that the OS still claims. The application can
  report that state clearly, not force a hardware reset.

## Decisions

### D1: A dialog-local explicit page-count flag

Add `_flatbed_page_count_explicit` to the scan dialog. It is set only by
the user selecting `All` while the current source is a flatbed. It is
reset when the source leaves the flatbed, when the device changes, and
when a new dialog is created. It is not persisted.

The `num_pages` setter uses the flag through a small predicate:

```text
newval == 1                                   -> allow
source is not a flatbed                       -> allow
allow-batch-flatbed is off                    -> reject
newval == 0 and not explicit                  -> reject
otherwise                                     -> allow
```

This allows finite counts above one on a flatbed when batch scanning is
enabled, but refuses an inherited or saved `All`. A profile or saved
default that requests `All` while a flatbed is selected is therefore
refused; the user can still choose `All` explicitly afterwards.

On entering the flatbed source, the source-change callback resets the flag
and selects one page when it is not set. The existing branch that ghosts
the `# Pages` frame when batch scanning is disabled stays. With batch
scanning enabled the frame stays sensitive, so the user can choose a count
or `All` deliberately.

The flag is set in the `All` click handler, not in the `num_pages` setter.
That distinction matters: `_do_changed_num_pages` and profile application
also assign `num_pages`, and none of those are a user choice on the
flatbed. Keeping the flag out of the setter avoids treating a programmatic
sync as consent to an unbounded batch.

Alternative considered: an origin enum (`adf-default`, `user`, `profile`)
is more expressive, but the only dangerous value is `0`; a boolean is
enough and is easier to reset.

### D2: Cache the flatbed-source state

Replace repeated `flatbed_selected(self.thread.get_option_value)` calls in
the dialog with `_refresh_flatbed_source()` and a cached
`flatbed_source_selected` value. The cache is refreshed when the options
are loaded, when the source option changes, and when the device changes.
The page-count predicate and the `# Pages` visibility checks read the
cache, not the worker.

If the refresh fails (a timeout or a backend exception), keep the last
known value, log the failure, and continue. Treating an unreadable source
as a flatbed is the safe default for the page-count guard: it prevents an
unbounded batch rather than allowing one. This also prevents a source-change
callback from aborting before it reaches the page-count assignment.

`scan_menu_item_mixins._flatbed_source_active()` should read the dialog's
cached value instead of calling `flatbed_selected()` itself. This removes
another synchronous option read from a UI callback.

### D3: A batch token separates user cancel from natural end

Add an integer batch token to `SaneThread`. `scan_pages()` increments it,
stores it as the active token, resets `_batch_cancelled`, and passes the
token through the `scan_page` closures. Both terminal callbacks check the
token before doing anything:

```text
response belongs to a superseded token  -> ignore
response belongs to the active token    -> import the page if present
batch cancelled                         -> finish, do not re-queue
page limit reached or feeder empty      -> end the batch, do not re-queue
otherwise                               -> queue the next scan_page
```

The import happens before the cancelled check, so a page whose transfer
completed before the cancel remains in the document. The check prevents
only the next acquisition.

Split the two meanings of `cancel()`:

- `cancel()` is the user-facing cancel. It marks the batch cancelled,
  drains queued requests, queues the device cancel, and performs the
  best-effort direct cancel. It does not invalidate the active token: the
  in-flight response still needs to run once so a page that completed
  before the cancel is imported and the finished callback runs.
- `_end_batch()` is the internal natural end. It queues the device cancel
  without marking the batch cancelled. It is used when the page limit is
  reached, the feeder is empty, or a scan error occurs.

The terminal callback invalidates the active token after it has imported
the completed page and notified the finished callback. A stale terminal
response from an old token is therefore ignored, including its finished
callback, so it cannot hide a new batch's progress bar.

Alternative considered: checking `_cancel_requested` in the finished
callback is smaller, but `do_scan_page` resets that flag for the next page
and the natural end also uses it. The token makes the distinction explicit
and testable.

### D4: Bounded recovery when a backend ignores cancel

`device_handle.cancel()` is already best-effort. If the backend raises
without unblocking `snap()`, the queued `cancel` request cannot run because
the worker is blocked. Add a watchdog in the dialog:

- `cancel_scan()` starts a one-shot GLib timeout after calling
  `thread.cancel()`.
- If the batch reaches a terminal callback first, the timeout is removed.
- If the timeout fires and the worker still reports an in-flight transfer,
  the dialog asks the thread to abandon the batch: mark it cancelled,
  invalidate the token, and drop the abandoned request's callbacks so a
  late response cannot import or re-queue it. The failure is then reported
  through the process-error path so the progress bar hides and Scan becomes
  sensitive again.
- Attempt a best-effort `device_handle.close()` from a short-lived helper
  thread with its own timeout. If it returns, clear the handle so the next
  scan can reopen the device. If it does not, record that the device is
  stuck and report it.
- The next scan rebuilds the device session. If the OS still holds the
  device, the existing device-open error path reports "Device busy" or the
  backend's error instead of hanging.

The watchdog starts only after a user cancel, not during normal scanning,
so a legitimately slow page is not treated as a failure. A five-second
grace period is the initial value; it is a local constant and can be tuned
after hardware testing.

Alternative considered: blocking the GTK thread on `close()` is rejected
because it freezes the UI. A patched `snap()` that polls a cancel flag
between reads is the robust long-term fix, but it belongs in the external
`python-sane`/`_sane` dependency.

### D5: Connect the progress-bar Cancel once

Connect `self._scan_progress.clicked` to `self._windows.cancel_scan` once
when the scan dialog is created, instead of on every `started-process`
event. The handler is harmless when no scan is running. Remove the
per-event connect and the now-unused disconnect bookkeeping from the
started/finished/error callbacks.

This makes one click issue one cancel. It also removes an accumulating
handler list that could call `cancel()` several times for one click.

### D6: Defensive guard in `scan()`

Before starting a scan, `SaneScanDialog.scan()` re-checks the invariant:
if the source is a flatbed and `num_pages == 0` but the explicit flag is
not set, force one page and log a warning. The facing pass of a
double-sided workflow is exempt because it is bounded by the reverse pass.
This is a backstop for a stale profile or a future regression; the dialog
remains the single place that decides the page count, and the thread
continues to trust the value it is given.

### D7: Tests

- Widget tests for source defaults: ADF `All` to flatbed, preference on
  and off, saved-profile `All`, re-entry, explicit `All` warning, finite
  count clearing it, and ADF `All` unchanged.
- Thread tests with the refilling flatbed fake: cancel from
  `new_page_callback` after the second page; assert the second page is
  kept, no third page is acquired, the finished callback runs, and a new
  one-page batch succeeds.
- A stuck-backend test with a fake whose `cancel()` raises without setting
  the cancel event; assert the watchdog path fails the batch as cancelled
  and a subsequent batch starts once the fake releases.
- A progress-bar wiring test: several started/finished events, one click,
  one `cancel_scan` call.
- Existing tests that assert the old inherited-`All` behaviour are updated
  to the new contract, not deleted.

## Risks / Trade-offs

- [Switching from ADF `All` to flatbed now changes the page count] →
  Intentional. The user can still choose `All` on the flatbed, and the
  dialog identifies it. Document the change in README and changelog.
- [The explicit flag is not persisted] → A new dialog always starts safe;
  a saved `All` profile is refused on a flatbed. This is the point.
- [A truly wedged device may remain claimed by the OS] → The watchdog
  reports a clear error and keeps the UI responsive; a new scan succeeds
  once the device is released. It cannot force a hardware reset.
- [The watchdog could fire during a legitimately slow cancel] → It starts
  only after a user cancel, uses a generous grace period, and a page that
  completes first cancels the watchdog.
- [Caching the flatbed state can go stale] → Refresh on source, options,
  and device changes; a failed refresh keeps the last value and treats an
  unknown source as a flatbed for the guard.
- [Token-guarded callbacks add state] → The token is a single integer
  passed through existing closures; tests cover cancel between pages, a
  new batch after cancel, and a stale response.
- [Connecting Cancel once means a click after the scan finishes calls
  `cancel_scan`] → `cancel()` is harmless when no transfer is active;
  tests confirm no error.

## Migration Plan

No configuration or data migration. The `allow-batch-flatbed` key and
default are unchanged; enabling it still permits multi-page flatbed
batches, but no longer inherits `All` from the ADF default. Release notes
must state that a flatbed batch now starts at one page and that `All` must
be chosen explicitly. Rollback is a plain revert.

## Open Questions

None that change the approach. The five-second recovery grace period is an
initial value to tune after hardware testing.
