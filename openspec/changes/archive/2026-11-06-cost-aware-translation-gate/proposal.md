# Proposal

## Why

The machine gate can compare translation quality but not cost. Its
`po/translation-gate.json` is still hand-written with placeholder endpoints,
and no call records the provider-reported token usage or price. A maintainer
therefore cannot answer the practical questions: which qualified model is
cheapest per accepted string, whether a qualification or drift probe is worth
running, or what a batch will cost before it starts. The OpenCode config
already carries provider URLs, model families, release dates, token limits and
per-million-token prices, so much of the gate configuration can be derived
rather than typed.

## What Changes

- Add `dev/sync_translation_gate.py` to generate or merge releases,
  deployments, model limits and prices from an OpenCode JSON or JSONC config,
  using a small `po/translation-gate.roles.json` file for the proposer and
  judge roles. It preserves thresholds and hand-edited fields, never copies a
  credential, and validates the result before writing.
- Extend `po/translation-gate.json` deployments with a `cost` block
  (`input`, `output`, `cache_read`, `cache_write`, USD per million tokens) and
  a `limits` block (`context`, `output`).
- Capture the usage object returned by an OpenAI-compatible provider, compute
  the cost of each call, and record it with the call evidence in the ledger.
  Add an optional `gate_runs` ledger section so abstentions are measurable
  too, not just approved strings.
- Add a `costs` report that compares releases and deployments by cost and
  quality per language: calls, tokens, spend, approvals and abstentions,
  approval rate, cost per approval, qualification and drift scores, and the
  observed defect rate.
- Add an `estimate` command for qualification, drift and gate actions. It
  estimates prompt and completion tokens from the actual source strings with a
  configurable character-to-token heuristic, reports a cost range per
  deployment, and can enforce a `--max-cost` budget before any request is
  made.
- Document the setup, sync flow, cost fields, estimate command and report in
  `po/README.md`.

Cost is advisory for model choice. It does not change the approval classes,
the independence rule, the high-impact rule or the defect-rate threshold.

## Capabilities

### New Capabilities

- `translation-gate-costing`: imports model identity, limits and prices from an
  OpenCode config; records provider usage and cost for every gate action;
  reports cost and quality per model; estimates an action's cost before it
  runs and can stop at a budget.

### Modified Capabilities

None.

## Impact

- **Tooling:** new `dev/sync_translation_gate.py`; changes to
  `dev/translation_gate.py` for usage capture, cost computation, the `costs`
  and `estimate` commands, and a budget guard; new tests under `dev/tests/`.
- **Configuration:** `po/translation-gate.json` gains `cost` and `limits`;
  new `po/translation-gate.roles.json`.
- **Ledger:** optional `gate_runs` records; machine approvals gain call
  evidence. No change to approval keys or provenance classes.
- **Docs:** `po/README.md` only; the root README stays a pointer.
- **Dependencies:** no new runtime dependency. JSONC input is handled by a
  small local normaliser, and token counts before a call use a documented
  heuristic rather than a tokenizer.
- **Security:** the sync reads environment variable names, never values, and
  refuses to copy literal `apiKey` or authorization headers.
