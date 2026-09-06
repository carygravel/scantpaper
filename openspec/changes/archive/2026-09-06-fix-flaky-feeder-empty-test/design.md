## Context

The batch-end cancel in the feeder-empty and cancel-raises tests is delivered
to the device by the worker thread via `do_cancel`, queued asynchronously by
`SaneThread.cancel()`. The direct synchronous device cancel in that method
(`image_sane.py:368`) is gated on `_scan_active`, which is `False` in the
batch-end paths this change touches, so only the queued request delivers it.

Both tests currently assert `FakeBrscan5Device.cancel_calls` immediately
after their batch `mlp.run()` returns, i.e. before the worker has necessarily
processed the queued cancel. On a starved worker (2-vCPU CI runner, loaded
suite) the main thread reaches the assertion first and `cancel_calls` is short
by one — `0 >= 1` in the feeder test (`image_sane.py.test_0821:824`), `1 >= 2`
in the cancel-raises test (`image_sane.py.test_0821:868`).

Verified measures under simulated 2-vCPU load (test pinned to 2 cores + 8 CPU
burners): feeder test fails 13/40, cancel-raises test fails 4/30. Both pass
in isolation on an idle 8-core box. See proposal.md — Why for motivation.

## Goals / Non-Goals

**Goals:**
- Make the `cancel_calls` assertions in the two racy tests deterministic
  without changing what they verify.
- Keep the existing synchronous-first assertion layout for the deterministic
  asserts (`pages`, `error.assert_not_called()`, `cancel_sent[0]`).

**Non-Goals:**
- No production-code changes: `SaneThread.cancel()`'s deliberate
  async-by-queue batch-end behaviour (design D3 of the archived
  cancel-scan-progress change) is untouched.
- Not touching the `_run_with_fake` sibling tests: they already assert after
  that helper's internal quit handshake and are deterministic.
- Not addressing the separate, rarer load mode where a `safe_mainloop(2000)`
  catches up and over-runs under extreme load; that is a different failure
  (safety-timeout) with a different remedy.

## Decisions

### D1: Assert `cancel_calls` after the final quit handshake

For both tests, move the `cancel_calls` assertion to follow the existing
`thread.send("quit", finished_callback=quit_mlp)` + `mlp.run()` block that
already terminates the worker.

Rationale: the worker's request queue is FIFO. By the time the batch
`finished_callback` runs, the queued cancel request is already enqueued
(`SaneThread.cancel()` runs before `_scan_pages_finished_callback` invokes the
caller's `finished_callback`). The test then sends `quit`, which is enqueued
behind the cancel. `do_quit` only runs after `do_cancel`, and `mlp.run()`
returns only when `do_quit`'s FINISHED response is processed — so when the
assertion runs, `do_cancel` has definitely completed. No sleeps, no polling,
no new synchronisation.

*Alternatives considered:*
- Keep the assertion where it is but poll for up to N ms until
  `cancel_calls` reaches the expected value. Timing-based; reintroduces a
  (smaller) race and a fixed sleep. Rejected.
- Assert only `pages`/`error` and drop the cancel-count check. Loses the
  spec-mandated "device session terminated" verification
  (`sane-page-acquisition`, Empty feeder ends the batch cleanly). Rejected.
- Make `SaneThread.cancel()` block until the worker delivers the device
  cancel. Production change, contradicts the archived design decision D3
  (batch-end cancel keeps single `do_cancel` queue behaviour), and adds
  main-thread/worker locking. Rejected.

### D2: Tighten `>= 1` to `== 1` where exact

After the quit handshake in the feeder test, exactly one cancel is delivered
(first page uses `no_cancel=True`; the feeder-empty scan raises at `start()`
before `snap()`). `== 1` documents that no stray cancel is delivered, matching
the sibling `_run_with_fake` tests' style (`cancel_calls == 1`). The
cancel-raises test keeps `>= 2` semantics (exactly two after the handshake:
one direct sync during the blocked snap, one queued at batch end) but may read
`== 2` for the same reason; the implementer should use the exact value and
assert on it.

## Risks / Trade-offs

- **[Test asserts a worker-side side-effect counter at all]** → Acceptable;
  it is the file's established idiom for "device session terminated" and is
  now deterministic. The counter is only read from the main thread after the
  handshake, never while the worker could be mid-update.
- **[FIFO ordering assumption could be broken by a future cancel path]**
  → The design relies on the request queue being strictly FIFO, which
  `basethread.send()` preserves. A future change that adds another
  batch-end cancel would surface here as an exact-count failure (`== 1`
  vs `== 2`), which is the desired regression signal.
- **[Worker never processes the queued cancel before `do_quit`]** → Cannot
  happen: `do_quit` is enqueued after `do_cancel` and the worker is
  single-threaded; processing is serial.

## Migration Plan

Internal-only; no data, config, or dependencies. Implement the test edits,
run `pytest` (full suite) and `ruff`, revert is reverting the two test hunks.