## 1. Fix the feeder-empty test

- [x] 1.1 In `test_feeder_empty_ends_batch_cleanly`,
      move `assert fake.cancel_calls >= 1` (currently line 824) to after the
      existing final `thread.send("quit", ...)` + `mlp.run()` handshake, and
      use the exact value `== 1`. Remove the `# FIXME: flaky` marker from the
      test signature.

## 2. Fix the cancel-raises test

- [x] 2.1 In `test_cancel_raises_on_device_terminates_cleanly`, move
      `assert fake.cancel_calls >= 2` (currently line 868) to after that
      test's final `thread.send("quit", ...)` + `mlp.run()` handshake, and use
      the exact value `== 2`.

## 3. Verify

- [x] 3.1 Confirm both tests fail pre-fix under simulated 2-vCPU load
      (test pinned to 2 cores with CPU burners running) and pass post-fix
      under the same load, plus pass in isolation on an idle box.
- [x] 3.2 Run the full test suite (`pytest`) — all tests pass and coverage
      remains at/above the configured threshold.
- [x] 3.3 Run `ruff check` and `ruff format --check`; both clean.