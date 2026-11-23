# Tasks

## 1. Proposer concurrency

- [x] 1.1 Add an order-preserving concurrency helper backed by a stdlib thread
  pool with an injectable seam, and switch `propose`/`propose_plural` to it;
  verify a two-proposer entry returns the same two proposals in the same order
  with identical evidence (`pytest dev/tests/test_translation_gate.py -k
  translate` passes with no output change).
- [x] 1.2 Prove the overlap with a fake client that blocks on a threading
  event, and verify the single-role path stays a single call; verify a failing
  proposer still aborts the batch exactly as today.

## 2. Judge deadline

- [x] 2.1 Add an optional per-call `timeout` override to `ModelClient` and
  `OpenAICompatibleClient.complete`; verify a call with the override uses it
  for the connection and a call without keeps the transport default.
- [x] 2.2 Give `ObservedClient` a `judge_timeout` that forwards the override
  only for judge-classified prompts; verify a judge prompt is sent with the
  deadline and proposer/back-translation prompts keep the transport timeout.
- [x] 2.3 Add `translate --judge-timeout` (documented default, `0` disables)
  threaded through `BatchRun.judge_timeout`; verify parsing and that the
  default and disabled forms reach the wrapper as specified.

## 3. Judge failure is an abstention

- [x] 3.1 Catch `ModelError` in `blind_judge`/`blind_judge_plural` and return
  an abstain verdict; verify a judge that raises `ModelError` records an
  abstained entry with the timeout reason, stays fuzzy, and the batch
  continues.
- [x] 3.2 Verify a missing credential still raises the hard error (not an
  abstention), and that a judge answering within budget produces the same
  decision and verdict as a run without the deadline.

## 4. Report surfaces the bound

- [x] 4.1 Add a `judge_abstained` count to `BatchReport`; verify a batch with a
  timed-out judge reports the count in both human and JSON forms, and a batch
  with none reports a zero count.

## 5. Integration and quality gates

- [x] 5.1 Run `pytest -m "not slow"`, `ruff check .`, `ruff format --check .`,
  `ty check .`, `python3 dev/check_test_coverage.py` and
  `openspec validate --specs --strict --no-interactive`; verify all are clean.

## 6. Documentation

- [x] 6.1 Document `--judge-timeout` and the concurrent-proposal note in
  `po/README.md`, and add the user-visible line to `changelog.md`; verify each
  documented command runs unmodified against a temporary fixture.
