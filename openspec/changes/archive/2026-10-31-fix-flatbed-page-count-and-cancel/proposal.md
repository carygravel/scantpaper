# Proposal

## Why

Scanning from a flatbed can turn into an unbounded batch: if `# Pages` is
`All`, the scan loop has no natural end, because a flatbed never reports
"document feeder out of documents". The loop can then outlive the user's
Cancel: a page completion that is already in flight queues the next page
after the cancel has drained the queue. If the backend's cross-thread
`cancel()` does not unblock the transfer, the worker remains in `snap()`,
every later scan request queues behind it, and the application needs a
restart. This breaks the existing guarantees that a cancelled scan stops
promptly and that the device is reusable afterwards.

The trigger is easy to reach. With "Allow batch scanning from flatbed"
enabled, the ADF default (`# Pages = All`) is inherited when the source is
switched to Flatbed, so the user is never asked to confirm an unbounded
flatbed batch. With the preference disabled the existing guard forces one
page, but the scan layer still has no defence against an unbounded flatbed
batch if the dialog state is ever wrong.

The outcome to guarantee is one user-visible behaviour: a flatbed batch
cannot run away, and cancelling one always leaves the application able to
scan again.

## What Changes

- A flatbed source no longer inherits the ADF `All` default. When the source
  changes to Flatbed, `# Pages` defaults to one page unless the user has
  explicitly chosen `All` (or a finite count) for the current flatbed
  session. The `# Pages` frame stays ghosted when batch flatbed is disabled,
  and stays editable when it is enabled so the user can still choose a
  multi-page flatbed batch deliberately.
- An unbounded flatbed batch is treated as an explicit choice, not an
  accidental inheritance. If `All` is selected on a flatbed, the dialog
  identifies it as an unbounded flatbed batch before scanning starts.
- Cancelling a scan batch invalidates that batch. No page from it is
  acquired or imported after the cancel, even when a page completion
  callback was already queued when the cancel arrived.
- A cancelled transfer that does not stop within a bounded time is
  recovered by resetting or reopening the device session, so a subsequent
  scan can start without restarting the application. If recovery itself
  fails, the failure is reported as an error, not as a normal end of
  batch.
- The progress bar's Cancel handler is connected once per scan dialog, not
  once per `started-process` event, so one click issues one cancel rather
  than an accumulating series of them.
- The flatbed `# Pages` default, the explicit-`All` state and the recovery
  behaviour are covered by specs. The existing cancel and reusability
  guarantees are strengthened where the current wording leaves the
  post-cancel re-queue and a backend that ignores cancel unaddressed.

## Capabilities

### New Capabilities

- `scan-source-defaults`: how `# Pages` and sided mode are chosen when the
  scan source changes, including the ADF-to-Flatbed transition, the
  batch-flatbed preference, and the difference between an inherited `All`
  and a user-chosen unbounded flatbed batch.

### Modified Capabilities

- `sane-page-acquisition`: cancelling a batch must prevent any further page
  from that batch being acquired or imported, including a page whose
  completion callback is already in flight, and a cancelled transfer that a
  backend does not interrupt promptly must be recovered so the device is
  reusable.
- `background-job-cancellation`: a cancelled scan batch must not queue
  further scan pages after the cancel, and the application must remain able
  to start a new scan afterwards.

## Impact

- `src/scantpaper/dialog/scan.py`: the source-change callback and the
  `# Pages` guard.
- `src/scantpaper/dialog/pagecontrols.py`: the page-count state and the
  explicit-`All` transition.
- `src/scantpaper/frontend/image_sane.py`: scan-batch identity, cancel,
  completion re-queue and worker/device recovery.
- `src/scantpaper/scan_menu_item_mixins.py` and
  `src/scantpaper/session_mixins.py`: progress-bar Cancel wiring and
  finished-process handling.
- Tests under `src/scantpaper/tests/` for source defaults, cancel between
  pages, a backend that does not honour cross-thread cancel, and a second
  scan after a cancel.
- No new dependencies and no configuration migration. The
  `allow-batch-flatbed` preference still permits multi-page flatbed
  batches; it no longer implies an unbounded batch.
- README/FAQ and `changelog.md` need a short note on the flatbed `All`
  behaviour and the recovery guarantee.
