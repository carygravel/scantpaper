## 1. Regression tests (write first)

- [x] 1.1 In `test_083_basethread.py`, add a test that a `running` callback
  which calls `send()` completes the dispatch pass without raising. Drive it
  through `monitor()` with no main loop so it is deterministic and fails
  today with `RuntimeError: dictionary changed size during iteration`.
- [x] 1.2 Add a test that a `running` callback raising an exception is
  routed to the request's `error_callback` with the failure as `status`.
  Fails today with `AttributeError: 'NoneType' object has no attribute
  'request'`.
- [x] 1.3 Add a test that a raising callback does not prevent later
  responses being delivered: send a second request after the failing one and
  assert its response is still dispatched.
- [x] 1.4 Add tests asserting each of `_on_readable`, `_drain_one` and
  `_tick` returns its GLib continue/remove value and does not propagate when
  the dispatch work raises.
- [x] 1.5 Confirm each new test fails against the current code, and records
  the failure reason in its docstring.

## 2. Error routing for callbacks invoked without a response

- [x] 2.1 In `basethread.py`, make the failure path of
  `_execute_single_callback` independent of the response argument, so a
  callback invoked with no response cannot raise while the failure is being
  reported.
- [x] 2.2 In `send()`, record the request in its registry entry, so a failing
  callback can still be reported by name once the response is gone.
- [x] 2.3 Route such a failure to the request's `error_callback` with the
  failure text as `status` and the recorded request, matching the behaviour
  when a response is present.
- [x] 2.4 Keep the log line informative when there is no response, naming the
  recorded request rather than inventing a process name.
- [x] 2.5 Verify task 1.2 passes.

## 3. Tolerant dispatch pass

- [x] 3.1 In `basethread.py`, iterate a snapshot of the request registry in
  the `running` branch of `_execute_callbacks_for_stage`, so callbacks that
  register or retire requests cannot invalidate the iteration.
- [x] 3.2 Confirm `_execute_stage_callbacks` still skips requests retired
  earlier in the same pass rather than dispatching against stale state.
- [x] 3.3 Verify tasks 1.1 and 1.3 pass.

## 4. Pump resilience

- [x] 4.1 Wrap the dispatch work of `_on_readable`, `_drain_one` and
  `_tick` so an exception is logged with `logger.exception` and the source
  returns its normal GLib value.
- [x] 4.2 Confirm no pump source can remove itself by raising, so the pipe
  watch, the drain chain and the progress tick each keep their role.
- [x] 4.3 Verify task 1.4 passes.

## 5. Verification

- [x] 5.1 Run `pytest` in full: all tests pass and coverage does not drop.
- [x] 5.2 Run `test_0821_frontend_image_sane.py` repeatedly to confirm the
  user-cancel scenario no longer depends on which GLib source happens to be
  dispatching.
- [x] 5.3 Confirm the previously reported runtime error no longer appears in
  the log output of the cancel tests.
- [x] 5.4 Run `ruff format` and `ruff check` with no new suppressions, and
  `ty check .` with no diagnostics.
- [x] 5.5 Update `README.md` only if anything user-visible changed; record
  in the change notes that the fix restores already-documented behaviour.
