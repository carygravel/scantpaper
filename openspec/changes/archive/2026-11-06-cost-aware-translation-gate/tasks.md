# Tasks

## 1. Configuration schema

- [x] 1.1 Add optional `cost` and `limits` blocks to a deployment in
  `po/translation-gate.json`, validate currency, unit, non-negative prices and
  non-negative token limits, and verify a config with and without them loads.
- [x] 1.2 Add a pinned prompt version and derived prompt hash in
  `dev/translation_gate.py`, use it in deployment identity and gate evidence,
  and verify changing the version changes the identity.
- [x] 1.3 Add `po/translation-gate.roles.json` with proposer and judge
  deployment ids, validate that the ids exist and the families are
  independent, and verify an unknown role or a duplicate family is rejected.

## 2. Structured completions and usage

- [x] 2.1 Add `Usage` and `Completion` values; make the
  OpenAI-compatible client parse common usage shapes and latency, and verify
  prompt, completion, cached and missing-usage cases with mocked responses.
- [x] 2.2 Add cost calculation over input, output, cache-read and cache-write
  prices; verify uncached, cached and missing-price cases, and record unknown
  cost rather than zero.
- [x] 2.3 Update qualification, proposal, judging, back-translation and drift
  call sites to consume `Completion` and retain every call, and verify mocked
  gate runs still approve only on complete evidence.
- [x] 2.4 Add the optional `gate_runs` ledger section, record approved and
  abstained gate outcomes with calls, tokens, cost and latency, and verify an
  abstention is measurable.
- [x] 2.5 Record call summaries in qualification and drift records, and verify
  the existing approval and qualification contracts still validate.

## 3. OpenCode import

- [x] 3.1 Add a small JSONC normaliser handling comments and trailing commas
  outside strings, and verify it accepts the two config shapes and rejects
  malformed input.
- [x] 3.2 Discover OpenAI-compatible providers in both V2 `providers` and
  legacy `provider`, mapping base URL, environment variable names, model id,
  family, release date, costs and limits, and verify non-compatible providers
  are skipped.
- [x] 3.3 Add the role policy loader and a merge that preserves thresholds and
  manual deployment fields; verify a second import is identical and `--force`
  replaces them.
- [x] 3.4 Add the sync command with `--opencode`, `--roles`, `--dry-run`,
  `--force` and validation before writing; verify a literal key is never
  copied and an invalid config is not written.
- [x] 3.5 Document the sync, role file and security rule in `po/README.md`,
  and verify the documented command runs with a fixture and leaves no secret.

## 4. Cost/performance report

- [x] 4.1 Aggregate `gate_runs`, qualifications and drift records by
  language, release and deployment, including unknown costs, and verify two
  deployments with different approval rates and spend are compared.
- [x] 4.2 Add the `costs` command with text and `--json` output, including
  abstentions, approval rate, cost per approval and available quality scores,
  and verify a model that mostly abstains is not presented as cheap.
- [x] 4.3 Document the report fields and how to read cost per approval in
  `po/README.md`, and verify the documented command runs.

## 5. Pre-action estimates and budget

- [x] 5.1 Add the character-to-token heuristic with a configurable
  `chars_per_token`, output bounds from model limits, and verify low/high
  estimates for short and long strings.
- [x] 5.2 Add `estimate` for qualification, drift and gate actions with text
  and `--json` output, and verify the gate estimate includes two proposers, a
  judge and back-translation.
- [x] 5.3 Add a `--max-cost` guard to the gate action and optional budgets to
  qualification and drift, and verify an over-budget run makes no request and
  names the estimate and budget.
- [x] 5.4 Document the estimate assumptions and budget guard in
  `po/README.md`, and verify the documented commands run with a fixture.

## 6. Integration verification

- [x] 6.1 Run `pytest`, `python3 dev/check_test_coverage.py`,
  `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_po.py` and
  `openspec validate --specs --strict --no-interactive`; verify no new
  uncovered lines, partial branches, lint, type or catalog errors.

## Workflow follow-up

- Archive the change after review and verify the archived result.
