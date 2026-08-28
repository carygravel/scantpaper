# cancel-progress-jobs

## Why

The Cancel button on the progress bars only hides the bar; the underlying scan, import, or save job keeps running to completion in the background. The PID-tracking and process-killing machinery it was designed to call exists but was never wired together, leaving the FIXME at `scantpaper/file_menu_mixins.py:245` and a number of commented-out calls behind.

## What Changes

- Make the Cancel button on progress bars genuinely cancel work: it both hides the bar and issues a cancellation to the document thread.
- Connect the progress bar's cancel signal to `Document.cancel()` with the intended cancel/process callbacks instead of the stale, commented-out `slist.cancel([pid])`.
- Populate the `running_pids` registry of the background thread so that `Document.cancel()` actually kills spawned subprocesses (today the registry is initialized empty and never filled, making its kill loop dead code).
- Route subprocesses that currently bypass the PID-tracking path (e.g. `tiffcp`, `ddjvu`, `djvused`, `pdfimages`, `pdftotext`, `qpdf`, unpaper, post-save hooks) through the PID-tracking mechanism so long-running children are killable, not just interruptible between steps.
- Remove the `# FIXME: import_files() now returns an array of pids.` comment and the duplicate FIXME in `basedocument.cancel()` (`# FIXME: move most of this to basethread.py`) once the wiring is complete and accurate.
- Update unit and integration tests so the Cancel interaction (button click → job cancelled) is exercised end to end, not only by calling `slist.cancel()` directly.

## Capabilities

### New Capabilities
- `background-job-cancellation`: Governs what happens when the user cancels background work (import, save, scan post-processing): queued jobs are dropped, the running job stops, spawned subprocesses are terminated, no partial output is presented as completed, and the document remains usable afterwards.

### Modified Capabilities
- `progress-bar-lifecycle`: The progress bar's cancel button SHALL initiate cancellation of the running/queued work it reports on, rather than merely hiding and disconnecting its signal.

## Impact

- `scantpaper/progress.py` — cancel closure wires to `Document.cancel()`.
- `scantpaper/basedocument.py` — `cancel()` kill loop becomes live; registry semantics reconciled (list vs dict).
- `scantpaper/importthread.py`, `scantpaper/savethread.py`, `scantpaper/docthread.py`, `scantpaper/page.py` — subprocess launches and PID registration.
- `scantpaper/helpers.py` — `exec_command()` PID-file registration hook.
- `scantpaper/file_menu_mixins.py` — FIXME (W0511) resolved.
- Tests: `tests/test_progress.py`, `tests/test_basedocument.py`, import/save integration tests.