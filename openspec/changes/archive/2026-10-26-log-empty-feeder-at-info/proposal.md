# Proposal

## Why

When a SANE backend reports `Document feeder out of documents`, scantpaper
correctly treats it as the normal end of a feeder batch: the pages already
acquired are kept, no error dialog appears, and the scan finishes. The logging
contradicts that handling. `SaneThread.handler_wrapper()` logs every exception
with `logger.exception()` *before* it checks for the clean feeder-empty case,
so a routine batch end produces an ERROR line and a full traceback ending in
`_sane.error: Document feeder out of documents`.

Users are asked to attach `--log` output to bug reports, so that traceback is
read as a scan failure. In the report that prompted this change it was the
only feeder-related error, although two pages had been acquired and saved, and
it invited the conclusion that the front feeder had not been recognised. The
noise also makes genuine feeder errors harder to find in the same log.

## What Changes

- Classify the feeder-empty exception as a clean end of batch before logging
  it. Log one INFO line without a traceback (for example, "Document feeder is
  empty; ending the scan batch"), naming the reason in plain language.
- Keep the existing exact-string match and the existing routing through
  `request.finished(None, status)`, so the batch still ends, the acquired pages
  are kept and the session is terminated exactly as before.
- Keep ERROR plus traceback for every other exception, including an
  unexpected `scan_page` failure and a device error mid-batch.
- Add regression tests: a feeder-empty batch must emit no ERROR record and no
  traceback; a real device error must still emit both.
- Add a changelog entry.

No scan behaviour, option, dialog or output-file change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `sane-page-acquisition`: add the guarantee that a feeder-empty batch end
  (`SANE_STATUS_NO_DOCS`) is reported as a normal lifecycle event - never as an
  application error with a traceback - while genuine device errors keep their
  ERROR log. The existing clean-end handling itself does not change.

## Impact

- `src/scantpaper/frontend/image_sane.py`: guard the logging in
  `SaneThread.handler_wrapper()` so the feeder-empty case is logged at INFO
  without `exc_info`; leave the other branches unchanged.
- `src/scantpaper/tests/test_0821_frontend_image_sane.py`: assert log records
  for the clean and failing paths, in addition to the existing response and
  cancel assertions.
- `specs/sane-page-acquisition/spec.md` (delta in this change): the new
  logging guarantee, synced to `openspec/specs/` when the change is archived.
- `changelog.md`: user-visible entry under the unreleased version.
- No README, UI, CLI, dependency or data-format change.
