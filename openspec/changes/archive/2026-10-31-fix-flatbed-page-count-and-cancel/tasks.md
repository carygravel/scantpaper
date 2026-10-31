# Tasks

## 1. Flatbed page-count default

- [x] 1.1 Add `_flatbed_page_count_explicit` to the scan dialog, set it only
  from the `All` click handler while the source is a flatbed, and reset it on
  source leave, device change, and dialog creation. Verify with a widget test
  that ADF `All` followed by a flatbed source yields one page.
- [x] 1.2 Refactor the `num_pages` setter into a predicate that allows one
  page, refuses `All` on a flatbed unless the explicit flag is set, and still
  allows finite counts above one when batch flatbed is enabled. Verify with
  tests for preference on/off, a saved profile containing `All`, and a
  finite count.
- [x] 1.3 Add the unbounded-batch indication label under the `# Pages` frame
  and update its visibility on page-count, source, and preference changes.
  Verify that it is visible for `All` on a flatbed, hidden for a finite count
  and for `All` on an ADF.
- [x] 1.4 Add the defensive guard in `SaneScanDialog.scan()`: a flatbed with
  `num_pages == 0` and no explicit choice is forced to one page and logged.
  Verify with a test that the scan starts with one page in that state.
- [x] 1.5 Cache the flatbed-source state and use it in the dialog and in
  `scan_menu_item_mixins._flatbed_source_active()`. Verify with a test that a
  timeout or exception from `get_option_value()` during a source change does
  not abort the callback and does not leave `# Pages` on `All`.
- [x] 1.6 Document the new flatbed default in README/FAQ and `changelog.md`.
  Verify the documented steps match the widget behaviour.

## 2. Batch token and cancel

- [x] 2.1 Add the batch token and `_batch_cancelled` state to `SaneThread`,
  reset them in `scan_pages()`, and pass the token through the `scan_page`
  closures. Verify with a unit test that a new batch gets a new token and
  clears the cancelled flag.
- [x] 2.2 Split the user-facing `cancel()` from the internal `_end_batch()`
  and use `_end_batch()` for page-limit, feeder-empty, and scan-error ends.
  Verify that a natural end does not mark the batch cancelled and a
  subsequent batch starts normally.
- [x] 2.3 Token-guard `_scan_pages_finished_callback` and the cancelled
  callback: import a completed page, then stop without re-queuing when the
  batch is cancelled. Verify with the refilling flatbed fake that cancelling
  after page 2 keeps page 2, acquires no page 3, and invokes the finished
  callback.
- [x] 2.4 Ignore terminal responses from a superseded batch so they cannot
  import a stale page or hide a new batch's progress bar. Verify with a test
  that starts a new batch before the old response is delivered.
- [x] 2.5 Add the regression test that cancels from `new_page_callback` while
  the flatbed batch has no page limit. Verify that it fails against the old
  re-queue behaviour and passes with the token guard.

## 3. Recovery when a backend ignores cancel

- [x] 3.1 Add the one-shot recovery watchdog to `SaneScanDialog.cancel_scan`
  and remove it when the batch reaches a terminal callback. Verify with a
  test that it does not fire for a normal cancel and does fire for a blocked
  fake backend.
- [x] 3.2 Add `SaneThread.abandon_batch()` with a best-effort device close
  from a short-lived helper thread. Verify that the active request is failed
  as cancelled and the worker is marked unusable for the current session.
- [x] 3.3 Rebuild the device session on the next scan after a recovery.
  Verify that a second batch succeeds once the fake backend releases, or
  reports a clear device-busy error rather than hanging.
- [x] 3.4 Surface the recovery failure through the existing process-error
  path and reset the cursor and Scan button. Verify that the progress bar is
  hidden and Scan is sensitive after the watchdog fires.
- [x] 3.5 Document the recovery guarantee and the device-busy limitation in
  README/FAQ and `changelog.md`. Verify the text matches the observed
  behaviour.

## 4. Progress-bar Cancel wiring

- [x] 4.1 Connect the progress bar's Cancel handler once when the scan dialog
  is created instead of on every `started-process` event. Verify that one
  click after several started/finished events calls `cancel_scan` once.
- [x] 4.2 Remove the obsolete per-event disconnect bookkeeping from the
  started, finished, and error callbacks. Verify the existing process-error
  and finished-process tests still pass.

## 5. Integration and quality gates

- [x] 5.1 Run the full `pytest` suite. Verify all tests pass and the
  uncovered and partially covered line counts are the same or better.
- [x] 5.2 Run `ruff format --check`, `ruff check`, and `ty check .`. Verify
  there are no errors or new suppressions.
- [x] 5.3 Run `openspec validate "fix-flatbed-page-count-and-cancel"`.
  Verify the change validates.
- [x] 5.4 Exercise the reported scenario end to end with the fake backend,
  or a real scanner if available: ADF `All`, switch to flatbed, scan, cancel,
  then start a new scan. Verify the batch stops after the current page and
  the new scan works without restarting the application.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived `scan-source-defaults`, `sane-page-acquisition`, and
  `background-job-cancellation` specs.
