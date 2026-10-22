## 1. Break the callback cycle in generated methods

- [x] 1.1 In `BaseDocument._modify_method_generator`, call
  `_note_callbacks(kwargs)` before constructing the data callback, then build
  `partial(self.data_callback, options=dict(kwargs))` and pass it to the
  thread method as a separate `data_callback=` keyword instead of storing it
  in `kwargs`.
- [x] 1.2 Confirm the thread helpers in `importthread.py` still pop the
  callback from `**kwargs` into the send callbacks, so the request args remain
  callback-free.
- [x] 1.3 Add a unit test that a generated method's request options do not
  reference the callback passed to the worker, and that a weak reference to
  the options dies by reference counting without `gc.collect()`.

## 2. Break the cycle in direct document methods

- [x] 2.1 Change `Document.import_file` to keep
  `_import_file_data_callback` out of `kwargs` and pass it to
  `self.thread.import_file` as a separate keyword.
- [x] 2.2 Apply the same separate-callback pattern to `Document.split_page`,
  `Document.unpaper`, and `Document.user_defined`.
- [x] 2.3 Leave `Document.import_scan`'s copy-based construction in place and
  add a regression assertion that it remains cycle-free.
- [x] 2.4 Add a test that a completed import request's options and callback
  become unreachable without a cyclic-GC pass.

## 3. Release PID files deterministically

- [x] 3.1 In `Importhread._request_completed`, after popping the pidfile from
  `running_pids`, close it under `self.lock`, logging and suppressing close
  errors rather than raising.
- [x] 3.2 Ensure requests drained as queued-and-unstarted also release their
  pidfile, either by extending `drain_cancelled_requests` in
  `Importhread` or by adding a worker hook that runs the same cleanup for
  each drained request.
- [x] 3.3 Make the cancellation reader tolerate a pidfile that is already
  closed or empty, without attempting to kill the wrong process.
- [x] 3.4 Add tests that a completed request's pidfile descriptor is closed
  before its terminal callback returns, that a running request's pidfile
  remains readable by `cancel()`, and that draining a queued request closes
  its pidfile.
- [x] 3.5 Add a regression test that runs many OCR requests in one worker
  without an explicit `gc.collect()` and asserts that completed requests add
  no open descriptors; use `os.fstat()` on recorded descriptors or an
  equivalent check that does not treat deleted files as closed.

## 4. Fix the PID-file error report

- [x] 4.1 Pass the process name to `create_pidfile()` from its three call
  sites (`_note_callbacks`, file-information setup, and `import_file`).
- [x] 4.2 On failure, construct a minimal `Request` carrying the options and
  process name, wrap it in an `ERROR` `Response`, and invoke the configured
  error callback once with that response; include the temporary directory and
  the original `OSError` in the response status.
- [x] 4.3 Update `test_create_pidfile_error` and any other test that uses the
  old three-argument callback contract, and add a test asserting no
  `TypeError` occurs and the original OS error is present in the reported
  message.
- [x] 4.4 Keep `create_pidfile()` returning `None` on failure and verify the
  caller continues without a pidfile, with the error surfaced once.

## 5. Verify callback semantics and long-run behaviour

- [x] 5.1 Run the OCR, rotate, threshold, unpaper, and user-defined tests and
  confirm that data callbacks and post-processing still receive the same
  option values (including `pidfile`, `dir`, and the post-process selector).
- [x] 5.2 Re-run the import and multi-page PDF tests and confirm page rows,
  thumbnails, and metadata are unchanged.
- [x] 5.3 Exercise a batch large enough to cross the old accumulation point
  under a normal descriptor limit, or a scaled-down unit-level equivalent,
  and confirm no `EMFILE` occurs and the open-descriptor count returns to
  baseline.

## 6. Documentation and quality gates

- [x] 6.1 Add a bullet under `## 4.0.0 (unreleased)` in `changelog.md`
  describing the fixed descriptor exhaustion and the restored error report.
- [x] 6.2 Confirm `README.md` has no section documenting the old failure; if
  it does, update it, otherwise note in the change that only the changelog
  needed a user-visible entry.
  - Confirmed: `README.md` has no PID-file or descriptor-exhaustion section;
    only `changelog.md` needed a user-visible entry.
- [x] 6.3 Run `pytest` and confirm all tests pass and the uncovered and
  partially covered line counts are the same or better.
- [x] 6.4 Run `ruff check .`, `ruff format --check .`, and `ty check .` with no
  diagnostics.
- [x] 6.5 Run `PYTHONPATH=src python3 dev/check_po.py` if any translated
  string changed; otherwise confirm no translation changes were needed.
