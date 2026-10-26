# Tasks

## 1. Log the clean feeder-empty batch end at INFO

- [x] 1.1 In `SaneThread.handler_wrapper()`, test for the feeder-empty status
      before logging, emit one INFO record such as
      `"Document feeder is empty; ending scan batch: %s"` without `exc_info`,
      and keep routing through `request.finished(None, str(err))`; verify with
      `pytest src/scantpaper/tests/test_0821_frontend_image_sane.py`.
- [x] 1.2 Extend `test_feeder_empty_ends_batch_cleanly` with `caplog`
      assertions that the batch end emits no ERROR record and no exception
      traceback, and one INFO record; verify that test passes.
- [x] 1.3 Extend `test_mid_batch_error_reports_and_terminates` with `caplog`
      assertions that a genuine device error still emits an ERROR record with
      a traceback; verify that test passes.
- [x] 1.4 Add the changelog entry under the unreleased 4.0.2 section,
      describing only the log-level change; verify the entry renders and does
      not claim a scan-behaviour change.

## 2. Verification

- [x] 2.1 Run `pytest`, `ruff check .`, `ruff format --check .`, `ty check .`
      and `openspec validate log-empty-feeder-at-info --strict`, and confirm
      all pass with no new uncovered or partially covered lines.

## Workflow follow-up

- Archive the change after review, which syncs the delta into
  `openspec/specs/sane-page-acquisition/spec.md`.
- No README change: no user-visible option, workflow or output change.
