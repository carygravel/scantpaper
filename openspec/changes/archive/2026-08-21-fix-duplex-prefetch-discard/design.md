## Context

See proposal.md for motivation. Key mechanics:

- `SaneThread.do_scan_page()` (scantpaper/frontend/image_sane.py) acquires one
  page via `device_handle.start()` + `device_handle.snap(progress=...)`.
- python-sane 2.9.2 `snap(no_cancel=False, ...)` calls `sane_cancel()` after
  the read loop on every path (success EOF *and* error) unless
  `no_cancel=1`. The parameter has existed since v2.8.0 (2015); python-sane's
  own `_SaneIterator` passes `True` for ADF scans.
- brscan5 (DS-740D etc.) buffers the next page as soon as the previous frame
  hits EOF; `sane_cancel()` discards that buffer; the following
  `sane_start()` then fails with SANE_STATUS_NO_DOCS.
- gscan2pdf's battle-tested loop (~20 years) defines the target semantics:
  - Dialog/Scan/Image_Sane.pm:523 - effective flag =
    `cancel-between-pages` setting AND `flatbed_selected()`;
  - Frontend/Image_Sane.pm:227-250 - cancel unconditionally at batch end
    (abort, page count reached, or error status); between pages only when the
    effective flag is set.
- scantpaper's dialog already computes that exact expression
  (dialog/sane.py:520-525), but nothing consumes it: the 2023 refactor
  (8e67b52) onto `snap()` dropped the consumer, so every page cancels today.

## Goals / Non-Goals

**Goals:**

- Duplex/multi-page feeder batches deliver every frame the backend captured,
  independent of the preference.
- Restore the gscan2pdf semantics as a faithful port rather than a new design.
- No leaked open session across batches, errors, user cancels, or device
  close.
- CI regression test reproducing #73's mechanism without hardware.

**Non-Goals:**

- Changing the scan loop architecture (staying with the `scan_pages` →
  `scan_page` callback chain rather than adopting python-sane's
  `_SaneIterator`, which lacks scantpaper's progress/callback model).
- Changing the preference's default value, storage key, or dialog wording -
  under restored semantics it scopes only the flatbed workaround, as designed.
- Fixing brscan5 itself or reporting upstream to Brother.

## Decisions

### D1: Consume the existing flag; pass it to snap()

Thread `cancel_between_pages` from `scan_pages()` through
`_scan_pages_finished_callback()` into `do_scan_page()` and call

```python
self.device_handle.snap(
    no_cancel=not self.cancel_between_pages_flag,
    progress=self._scan_progress_cb,
)
```

(python-sane's high-level `SaneDev.snap(no_cancel=False, progress=None)`
accepts both kwargs.) The dialog-side computation
(`setting AND flatbed_selected`) stays exactly where it is.

*Alternatives considered:* removing the preference in favour of pure
source-based selection, or flipping its default and asking affected users to
opt out - both rejected once the gscan2pdf source showed the AND with
`flatbed_selected()` already makes feeder behaviour preference-independent:
#73 is fixed for every setting value, stale configs stay inert, and the
preference keeps its documented purpose (bug-309 flatbed workaround).

### D2: Batch-end cancel issued by the thread, mirroring Image_Sane.pm

With `no_cancel=1`, python-sane never cancels - not even on error paths. So
`SaneThread` issues the cancel itself whenever a batch terminates, matching
gscan2pdf Frontend/Image_Sane.pm:235:

- NO_DOCS on `sane_start` (normal end of feeder batch),
- requested page count reached,
- exception raised by `do_scan_page` mid-batch (caught in
  `handler_wrapper`),
- user cancel (existing `do_cancel()` path),
- device close/quit (existing `close()` implies reset).

Implementation shape: enqueue the existing `cancel` process from the terminal
branches of `_scan_pages_finished_callback()` and from `handler_wrapper()`'s
error branch for `scan_page`. `sane_cancel()` is idempotent per the SANE
spec, so a redundant cancel after a user cancel is harmless; "exactly once"
is hygiene, not correctness.

### D3: Preference UI gains gscan2pdf's sensitivity coupling

In gscan2pdf the checkbox is insensitive unless flatbed batching is enabled
(`$cb_cancel_btw_pages->set_sensitive( $SETTING{'allow-batch-flatbed'} )`,
bin/gscan2pdf:7064). Copy this into preferences.py: the setting can only ever
matter when flatbed batching can produce a multi-page flatbed batch, so the
coupling communicates that scoping to users. Cosmetic; no data migration.

### D4: Regression test emulates brscan5 semantics on a fake handle

New tests in test_0821_frontend_image_sane.py style: patch the thread's
device handle with a scripted fake implementing #73's observed contract:

- `start()` succeeds while unbuffered frames remain, else raises
  "Document feeder out of documents";
- `snap()` returns the next buffered frame;
- `cancel()` drops all buffered frames.

Cases: feeder batch yields both sides of a duplex sheet (2 pages); before the
wiring exists the same test reproduces #73 (1 page, second start raises
NO_DOCS); flatbed with setting enabled cancels between pages; flatbed with
setting disabled does not cancel between pages but cancels at batch end;
page-limit termination cancels the session; mid-batch error reports and
cancels; user cancel terminates the session.

## Risks / Trade-offs

- [Flatbed multi-page batches lose implicit per-page cancel] Today every page
  cancels (snap() default); after the fix, a multi-page flatbed batch with
  the setting disabled leaves the session open across pages → Mitigation:
  this is gscan2pdf's 20-year default behaviour; single-page flatbed scans
  still always terminate via the batch-end path; users of backends that need
  per-page closes re-enable the setting built for exactly that (bug 309).
- [Prefetched frames discarded at page limit] With num_pages < frames
  buffered (e.g. duplex, num_pages=1), side 2 is fetched then dropped at
  batch-end cancel → Mitigation: matches scanimage --batch-count and
  gscan2pdf semantics; documented in the spec ("discarding any further
  buffered frames").
- [Double-cancel on user abort] User cancel plus batch-error-path cancel →
  harmless per SANE spec; no guard needed (YAGNI).
- [Backends requiring sane_start-after-cancel on feeders] Some hypothetical
  driver might misbehave when sane_start follows EOF without an intervening
  cancel → Mitigation: scanimage --batch and gscan2pdf have operated this way
  for decades; it is the SANE-spec-canonical pattern.

## Migration Plan

Single release; no config migration (key, default and stored values keep
their meaning). Rollback = revert commit.

## Open Questions

None.
