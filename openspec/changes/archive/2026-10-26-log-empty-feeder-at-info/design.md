# Design

## Context

See `proposal.md` - Why. Today `SaneThread.handler_wrapper()` in
`src/scantpaper/frontend/image_sane.py` catches every exception raised by the
worker handler, logs it with `logger.exception()` (ERROR plus traceback), and
only then classifies it: the feeder-empty status ends the batch through
`request.finished(None, status)`, a cancelled transfer through
`request.cancelled()`, everything else through `request.error()`. The
feeder-empty case is already the clean path in
`openspec/specs/sane-page-acquisition/spec.md` ("Empty feeder ends the batch
cleanly"); only the log record disagrees.

## Goals / Non-Goals

**Goals:**

- One observable change: a feeder-empty batch end is recorded as a normal
  event, not an error.
- Preserve the existing batch-end, page-retention and session-termination
  semantics exactly.
- Keep genuine device errors diagnosable with ERROR and a traceback.

**Non-Goals:**

- Generalising the detection to other backends' wording for "no documents".
- Changing the log level for a deliberate user cancel (pre-existing and
  separate).
- Changing user-facing error reporting or dialogs.
- Translating log text.

## Decisions

### Classify before logging

Restructure the `except` block so the feeder-empty test runs first, logs one
INFO line and returns early through the existing `request.finished()` call.
The alternative - log first and filter the record later - was rejected because
it hides the traceback machinery and is harder to test.

### INFO, without `exc_info`

Use `logger.info()` with the backend status in the message, for example
`"Document feeder is empty; ending scan batch: %s"`. The event is meaningful in
a support log, so INFO is preferable to DEBUG. Omitting `exc_info` drops the
traceback, which carries no diagnostic value for an expected event. Keeping
the status text in the message preserves searchability. Alternative: DEBUG -
rejected because the event is part of the normal scan lifecycle, not a
development detail.

### Keep the exact-string match and the finished() status

The match `str(err) == "Document feeder out of documents"` is the contract
with python-sane for `SANE_STATUS_NO_DOCS`; leave it unchanged. The status is
still passed as `request.finished(None, str(err))`, so
`_scan_pages_finished_callback()` continues to end the batch on
`response.status`. Introducing a dedicated exception type was rejected as an
out-of-scope backend/API change.

### Leave the cancel branch untouched

A deliberate cancel still reaches the unchanged `logger.exception()` call
before `request.cancelled()`. Demoting it may be desirable, but it is a
separate behaviour and would widen the blast radius of this change.

### Test records, not only behaviour

Extend the frontend tests with log assertions: the feeder-empty case must
produce no ERROR record and no exception traceback, and a mid-batch device
error must still produce both. Assert level and traceback presence rather than
the full wording, so the message can evolve.

## Risks / Trade-offs

- [The exception text is lost from the log] -> include the backend status in
  the INFO message; the status is also delivered to the finished callback.
- [An unexpected failure carrying the same string is demoted] -> the
  application already treats that string as a clean end and shows no dialog,
  so the log now matches the behaviour; the batch still ends and the pages are
  kept.
- [Tests couple to log wording] -> assert level and absence of a traceback,
  not the full sentence.
- [Log volume] -> one INFO line per batch end replaces one ERROR line plus a
  traceback, so output strictly decreases.

## Migration Plan

None. Log-only change; no configuration, data or API migration. Rollback is a
source revert.
