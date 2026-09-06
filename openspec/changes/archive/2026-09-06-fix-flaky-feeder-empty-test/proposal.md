## Why

`test_feeder_empty_ends_batch_cleanly`
(`scantpaper/tests/test_0821_frontend_image_sane.py:792`) is flaky: it
fails intermittently on `assert fake.cancel_calls >= 1` when the suite runs
on a loaded or low-core machine (e.g. CI's 2-vCPU GitHub runners). The
batch-end cancel is delivered to the device *asynchronously* by the worker
thread, but the test asserts the side-effect counter immediately after the
main loop quits, so a starved worker can still be holding the queued cancel
when the assertion runs. The flake is load-dependent, not isolated: it
reproduces deterministically under simulated 2-vCPU load (13/40 runs) and in
a loaded full-suite run, but never in isolation on an idle 8-core box.

## What Changes

- **`test_feeder_empty_ends_batch_cleanly`** — move `assert
  fake.cancel_calls >= 1` to *after* the existing final quit handshake
  (`thread.send("quit")` + `mlp.run()`). The request queue is FIFO and
  `do_quit` returns a FINISHED response, so the loop only returns once the
  queued `do_cancel` has run; the assertion becomes deterministic.
- **`test_cancel_raises_on_device_terminates_cleanly`** — apply the same fix
  to its `assert fake.cancel_calls >= 2` (line 868), which has the identical
  latent race (the second of the two cancels is the async queued one). It
  flakes 4/30 under the same simulated load.
- **Remove the `# FIXME: flaky` marker** from `test_feeder_empty_ends_batch_cleanly`.

The two tests keep asserting the same guarantees the spec requires
(session terminated at batch end; direct and queued cancels both attempted)
— only the observation point moves to a point where the async worker has
definitively delivered the cancel. `pages == [1]`, `error.assert_not_called()`,
and `assert cancel_sent[0]` remain where they are; they are deterministic
(serialized on the main loop) and are not part of the racy assertion.

No production code changes. This is a pure test-robustness fix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behavior changes — the batch-end session termination
already happens; only the test's observation of it changes. This change opts
out of specs via `skip_specs: true`.

## Impact

- **Code**: `scantpaper/tests/test_0821_frontend_image_sane.py` only.
  - `test_feeder_empty_ends_batch_cleanly` — `cancel_calls` assertion
    relocated after the quit handshake; FIXME removed.
  - `test_cancel_raises_on_device_terminates_cleanly` — `cancel_calls`
    assertion relocated after the quit handshake.
- **No production code, no API, no dependencies, no DB schema change.**
- The sibling tests that use `_run_with_fake` already assert after that
  helper's internal quit handshake and are therefore already deterministic;
  they are untouched.