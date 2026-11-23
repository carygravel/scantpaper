# Tasks

## 1. Reporter seam and estimate primitives

- [x] 1.1 Add a progress reporter with an injected clock (UTC wall time and a
  monotonic source) and pass it through `_run_batch`, defaulting to a no-op;
  verify `pytest dev/tests/test_translation_gate.py -k translate` passes with
  no output change.
- [x] 1.2 Add pure formatting for a rate, a five-minute-rounded duration band
  and a local completion time; verify unit tests with fixed UTC timestamps in
  a non-UTC zone assert the exact strings.
- [x] 1.3 Derive the duration prior from the language's recorded gate-run
  latencies, then the cross-language median, then a documented constant;
  verify one test per branch asserts the basis the reporter reports.

## 2. Start banner

- [x] 2.1 Print one banner before the first model request naming selected,
  skipped and unsupported entries, the spend estimate and the duration
  estimate with its basis; verify a test asserts the banner is emitted before
  the first recorded client call.
- [x] 2.2 Handle an empty selection: the banner states that nothing is
  selected and the run exits without a request; verify a test with a fully
  translated catalog asserts zero client calls and the banner text.

## 3. Per-entry progress and completion estimate

- [x] 3.1 Compute per-entry cost weights from the existing estimate and write
  one line per processed entry with position, approved and abstained counts,
  spend, rate and estimate; verify a three-entry fixture emits three lines
  with monotonic position and spend.
- [x] 3.2 Add `--progress {auto,line,none}` with terminal detection; verify
  tests assert a line per entry for `line`, silence for `auto` without a
  terminal, and `--json` stdout parsing as exactly one document.
- [x] 3.3 Estimate from the median of the last 20 entries and the 10th-90th
  percentile spread; verify a test with one outlier entry widens the band
  while moving the rate by less than the outlier alone.
- [x] 3.4 Add elapsed time and entries-per-hour to `BatchReport`, in both the
  human and JSON forms; verify the existing translate report tests still pass
  and a new test asserts both fields.

## 4. Batch state file

- [x] 4.1 Write `.cache/translate/<language>.json` atomically after each
  entry with the fields named in the design; verify a test reads it during
  and after a batch and that a second language writes a different path.
- [x] 4.2 Record the call in flight before each request and clear it on
  return; verify a client stub that reads the state file during a call sees
  the role and deployment, and that the field is empty afterwards.
- [x] 4.3 Keep the write advisory: a failed state write does not fail the
  batch; verify a test that makes the cache directory unwritable and asserts
  the batch still records its approvals.

## 5. `status` command

- [x] 5.1 Add `status` with a live source (state file) and an inferred
  source (recent ledger gate runs plus the catalog selection) reporting
  progress, spend, rate, estimate and freshness; verify tests cover both
  sources and the `--json` and `--language` forms.
- [x] 5.2 Classify running, stalled and abandoned from the recorded process,
  host, update age and waiting call; verify one test per state, including an
  unreadable state file falling back to inference.
- [x] 5.3 Verify `status` exits zero with no model credential present and
  prints no environment-variable name; test with a cleared environment.
- [x] 5.4 Document `status`, `--progress` and the operator/agent recipe in
  `po/README.md`; verify each documented command runs unmodified against a
  temporary fixture.

## 6. Bounded run and interrupt

- [x] 6.1 Add `--max-time`, checked between entries, reporting through the
  existing `stopped` field with completed and remaining counts; verify tests
  for a deadline reached between entries and for whichever of the cost and
  time budgets is reached first.
- [x] 6.2 Catch an interrupt, report completed, remaining, spend and the
  exact resume command, and exit 130 without a traceback; verify a test that
  raises `KeyboardInterrupt` inside the batch and asserts the output.
- [x] 6.3 Report batch progress and catalog completion as separate numbers
  and state that abstained entries are retried; verify a test with one
  abstention asserts both numbers and the retry note.
- [x] 6.4 Document `--max-time`, the interrupt and resume workflow and the
  new report in `po/README.md`, and add the user-visible line to
  `changelog.md`; verify the documented resume command runs in a temporary
  fixture.

## 7. Integration

- [x] 7.1 Run two languages concurrently in a temporary fixture with a fake
  client and the fixed clock; verify `status` lists both, and that banner,
  per-entry lines, state files and the final report agree on every count.
- [x] 7.2 Run `pytest -m "not slow"`, `ruff check .`,
  `ruff format --check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate --specs --strict --no-interactive`; verify all are
  clean.

## Workflow follow-up

- Archive the change after the maintainer approves the behaviour.
- Verify `openspec validate --archived --no-interactive` after archiving.
