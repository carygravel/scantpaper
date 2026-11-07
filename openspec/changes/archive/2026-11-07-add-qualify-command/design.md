# Design

## Context

See `proposal.md` - Why.

`dev/translation_gate.py` already contains the qualification machinery:

- `QualificationRequest(release, language, entries, approval_date, budget_usd)`
- `qualify_release(ledger, config, request, client)` scores exact reproductions
  of held-out entries, records the result under `(release, language)` and
  replaces an earlier record for the same pair.
- `estimate_qualification(config, request)` and `ensure_budget()` gate spend
  using the high end of the estimate.
- `_held_out(ledger, catalog, language, size)` selects deterministic,
  human-origin approvals joined to the language catalog.
- `OpenAICompatibleClient` reads the deployment's `key_env` only when a request
  is made.

The CLI exposes `estimate --action qualification`, which already performs the
same held-out selection and estimate, but it never calls a model. The ledger
is `po/translation-approvals.json`; 35 of the 44 catalogs currently have at
least 20 human-origin approvals, so the command has a usable baseline for
those languages.

## Goals / Non-Goals

**Goals:**

- One command that takes a release and language from catalog selection to a
  ledger qualification record.
- Spend control before the first model request.
- A readable result and a machine-readable `--json` form.
- Deterministic tests that never reach the network.

**Non-Goals:**

- Making `gate` refuse to call an unqualified release.
- Running qualification for every language or release in one invocation.
- Adding conformance or drift commands.
- Changing the qualification metric, tolerance or scoring.

## Decisions

### Add a `qualify` subcommand, not an execute flag on `estimate`

`estimate` stays side-effect free. A separate command makes the spending step
explicit and gives the parser room for the result-output options. The
alternative, `estimate --action qualification --execute`, would blur costing
and spending in one command and make accidental spend easier.

### Reuse `_held_out` and `qualify_release`

The command is a thin adapter: parse, load, select, estimate, check budget,
call, write, report. Duplicating baseline selection or scoring in the handler
would let the estimate and the real run drift apart.

### Command surface

- `--release` and `--language` are required.
- `--catalog` defaults to `po/scantpaper/<language>.po`.
- `--count` defaults to 20 and must be positive; `_held_out` divides by the
  count, so zero is rejected before selection.
- `--max-cost` is forwarded as `QualificationRequest.budget_usd`.
- `--json` prints the qualification record instead of the human summary.

This mirrors `estimate --action qualification`, so an operator can estimate
first and then run the same request.

### Recorded results and exit status

The command exits `0` when it writes a record, including `qualified: false`
and the no-baseline ineligible case. Those are valid outcomes, the same way an
abstention is valid for `gate`, and `--json` carries the `qualified` flag for
scripts. It exits non-zero only for an operational failure: unknown release,
unreadable catalog, missing credential, over-budget estimate or ledger write
failure. A `--require-qualified` flag would be a later addition if callers need
a shell-level gate.

### Validate before reading, write only after success

The handler checks that the release exists and has a deployment before opening
the catalog, so an unknown release fails cheaply. `polib` read failures are
caught and reported as errors. `qualify_release` mutates the in-memory ledger
only after its model calls succeed; `write_ledger` runs after it returns. Any
exception therefore leaves the on-disk ledger unchanged.

### Output

The human form reports release, language, score, tolerance, baseline size,
deployment, cost and the qualified or ineligible outcome. It omits the `calls`
array. `--json` prints the full record, including calls, so the evidence can
be archived or inspected.

## Risks / Trade-offs

- **First deployment only** → `qualify_release` uses the release's first
  configured deployment; other deployments still need conformance. This is
  existing behavior and stays documented rather than changed here.
- **No baseline** → a language without human-origin approvals records an
  ineligible result and spends nothing. The summary names the reason so it is
  not mistaken for a scoring failure.
- **Partial spend on a mid-run failure** → no record is written and the calls
  already made are not counted. The budget check limits the exposure; a future
  change could persist partial evidence.
- **Unknown prices** → `ensure_budget` refuses a budget it cannot evaluate.
  Without `--max-cost` the command runs, and the record keeps unknown costs as
  unknown.
- **Catalog drift** → held-out entries are joined to the current catalog by
  source key, so removed entries are skipped. The baseline size is recorded
  rather than assumed.
- **Credential leakage** → the command uses the existing client, which reports
  only the variable name and never the value.

## Migration Plan

No migration. The command is additive and the ledger schema already allows a
`qualifications` section. Rollback is removing the subparser and handler; any
records already written remain valid.

## Open Questions

None.
