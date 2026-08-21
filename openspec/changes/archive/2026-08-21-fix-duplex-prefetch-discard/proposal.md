## Why

Issue #73: on Brother DS-740D (brscan5, pass-through duplex ADF), scanning in
duplex mode delivers only the first side. python-sane's `snap()` calls
`sane_cancel()` after every page unless `no_cancel=True` is passed, and
scantpaper never passes it. brscan5 buffers the second side as soon as the
first is delivered; the per-page cancel discards it, and the next
`sane_start()` fails with SANE_STATUS_NO_DOCS, which scantpaper treats as a
clean end of batch.

gscan2pdf's scanner loop solved this years ago: its `cancel_between_pages`
flag is ANDed with `flatbed_selected()`, so document feeders are never
cancelled mid-batch. scantpaper's port already computes the identical flag in
dialog/sane.py, but the consumer was dropped in the 2023 refactor onto
`snap()`, leaving every scan with cancel-always behaviour.

## What Changes

- Thread the already-computed `cancel_between_pages` kwarg through
  `SaneThread.scan_pages()`/`scan_page()` into `do_scan_page()`, passing it to
  python-sane as `snap(no_cancel=not cancel_between_pages)`. Feeders therefore
  stop being cancelled between pages regardless of the preference, fixing #73
  for all settings.
- Terminate the SANE session explicitly at batch end (feeder empty, requested
  page count reached, or mid-batch error), mirroring gscan2pdf's
  Frontend/Image_Sane.pm - necessary because python-sane skips even error-path
  cancels when `no_cancel=1`.
- Keep the `cancel-between-pages` preference, key, checkbox and `False`
  default unchanged: under the restored semantics it scopes only the flatbed
  workaround, exactly as in gscan2pdf.
- Grey out the preference checkbox when flatbed batching is disabled,
  mirroring gscan2pdf's sensitivity coupling.
- README documents the duplex fix.

## Capabilities

### New Capabilities
- `sane-page-acquisition`: how scantpaper acquires pages from SANE devices -
  session lifecycle across multi-page batches, per-page vs per-batch cancel
  behaviour for ADF and flatbed sources, and end-of-batch detection via
  SANE_STATUS_NO_DOCS.

### Modified Capabilities

## Impact

- `scantpaper/frontend/image_sane.py`: consume the flag in `do_scan_page()`;
  add batch-end cancels in `_scan_pages_finished_callback()` and the
  `handler_wrapper()` error branch.
- `scantpaper/dialog/sane.py`: no functional change (already computes and
  passes the correct flag); test updates only.
- `scantpaper/dialog/preferences.py`: sensitivity coupling for the checkbox.
- Tests: new regression tests emulating brscan5 prefetch semantics against a
  mocked device handle; updates where scan wiring is asserted.
- `README.md`: document the duplex fix.
