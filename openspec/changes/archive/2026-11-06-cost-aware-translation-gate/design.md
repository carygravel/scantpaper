# Design

## Context

See `proposal.md` for motivation. The current gate already has a two-level
model identity (`release` and `deployment`), qualification and conformance
records, a ledger with optional sections, and a client that sends an
OpenAI-compatible chat-completions request. It discards the response's
`usage` object and has no price data, so no call can be costed.

`po/translation-gate.json` is hand-written. The local OpenCode config already
describes OpenAI-compatible providers with a base URL, environment variable
names, model families, release dates, token limits and per-million-token
prices. The gate needs the same facts plus explicit proposer/judge roles,
which OpenCode does not model.

## Goals / Non-Goals

**Goals:**

- Make cost a first-class property of a deployment and of every call.
- Use the OpenCode config as the source for model identity, limits and prices
  without copying credentials.
- Record enough usage to compare models after the fact, including abstentions.
- Estimate an action before spending and enforce a budget.

**Non-Goals:**

- No automatic model selection or cost-based approval rule. Cost is evidence
  for a maintainer, not a provenance class.
- No tokenizer dependency and no claim that a pre-action estimate is exact.
- No change to approval keys, evidence classes, independence or the
  high-impact rule.
- No background cost service or central price database.

## Decisions

### 1. Prices live on the deployment, not the release

A release is model identity: family, model id and revision. A deployment is
the serving configuration, and provider pricing belongs to it. Two providers
serving one release may charge differently, and a provider may change its
price without changing the model.

```json
"cost": {
  "currency": "USD",
  "unit": "per_million_tokens",
  "input": 0.6,
  "output": 3.3,
  "cache_read": 0.12,
  "cache_write": null
},
"limits": {
  "context": 256000,
  "output": 32768
}
```

`cost` and `limits` are optional so existing configs keep loading. A missing
price means the call cost is unknown, never zero.

Alternative considered: prices on the release. Rejected because a release
identity is not a billing identity, and a provider change would silently
change the meaning of every deployment.

### 2. The client returns a structured completion

`ModelClient.complete` returns a `Completion` carrying the text, the parsed
usage, latency and the deployment identity, instead of a bare string. Every
call site keeps the text for its existing logic and passes the completion to
the recorder. This avoids hidden client state and makes mocked clients report
usage in tests.

The parser accepts the common OpenAI-compatible shapes:
`prompt_tokens`, `completion_tokens`, `total_tokens`, and cached tokens from
`prompt_tokens_details.cached_tokens`, `cached_tokens`, or
`cache_read_input_tokens`. Cache writes are read from
`cache_creation_input_tokens` when present. A missing or malformed usage
object yields `usage: null`, not zeroes.

### 3. Cost calculation is explicit and conservative

The cost formula is:

```text
(input_tokens - cached_tokens) * input
+ cached_tokens * cache_read
+ cache_write_tokens * cache_write
+ completion_tokens * output
```

all divided by one million, rounded to six decimal places. Prices are stored
per million tokens in the configured currency.

If a required price is missing, or the provider omits usage, the call cost is
unknown with a reason. The gate never invents a zero. A cache token count with
no cache-read price is an unknown cost rather than a silent input-price
charge, because the two prices can differ by an order of magnitude.

Alternative considered: a local price table keyed by model. Rejected because
it drifts from the provider and duplicates the OpenCode data.

### 4. All actions are recorded, including abstentions

The ledger gains an optional `gate_runs` section. A gate run records the
action, language, release, deployment, outcome, reason, timestamp, calls,
total tokens, total cost and total latency. Each call in `calls` records the
deployment, release, model, token counts, cost and latency.

Qualifications and drift probes also record their call summary in their own
records. This keeps the existing audit trail readable while the cost report
can aggregate all actions. An abstained gate run has no approval record, so
`gate_runs` is what makes abstention cost visible.

Alternative considered: a separate cost database. Rejected because the
approval evidence and the cost must be reviewable together, and the ledger is
already the committed audit trail. `gate_runs` is optional and only written
by maintainer-run commands.

### 5. The cost report joins spend with quality

`translation_gate.py costs` groups `gate_runs`, qualifications and drift
records by language, release and deployment and reports:

- calls, input/output/cache tokens, spend and average latency;
- approvals and abstentions, and the approval rate;
- cost per approval;
- qualification score, drift score and defect rate where available.

The report supports text and JSON. A deployment with no price or no usage is
listed with unknown costs rather than omitted. Cost per approval is blank when
there are no approvals, not zero.

Alternative considered: report only token counts. Rejected because tokens are
not comparable across models with different prices, and the proposal is about
cost/performance.

### 6. Estimates are ranges based on a documented heuristic

The estimator uses `ceil(characters / chars_per_token)` with a configurable
`chars_per_token` default of 4. It does not bundle a tokenizer, because model
tokenizers vary and a new runtime dependency would be needed for every
provider family.

For each action the estimator reports a low and a high cost per deployment:

- **qualification:** one call per held-out entry, output estimated from the
  source token count up to the deployment's output limit;
- **drift:** one call per probe item, same output model;
- **gate:** two proposer calls, one judge call with a one-token answer, and
  one back-translation call for each sentence. The judge input includes both
  proposals; the back-translation input is the preferred translation.

The estimate is labelled as an estimate, with the heuristic and the token
assumptions in the JSON. Provider-reported usage after the action is
authoritative and is what the report aggregates.

Alternative considered: a tokenizer per provider. Rejected for dependency and
maintenance burden; the budget guard only needs a conservative range.

### 7. A budget guard runs before the first request

`gate` accepts `--max-cost`. The estimate is computed first; if it exceeds the
budget, the command exits non-zero and makes no request. The qualification and
drift functions accept the same budget through their call options. The message
names the estimate, the budget and the deployments that exceed it.

The guard is a pre-flight check, not a hard provider-side cap. A provider can
still return more output than estimated; the post-call cost is recorded and
the report shows the overrun.

### 8. OpenCode import maps identity and price, never credentials

A new `dev/sync_translation_gate.py` reads the OpenCode config. The mapping is:

| OpenCode | Gate |
| --- | --- |
| provider id | deployment `provider` |
| `env[0]` | deployment `key_env` |
| `settings.baseURL` or `api` | deployment `endpoint` |
| model map key or `modelID` | request model |
| model `family` | release family |
| model `releaseDate` | release revision |
| model `cost` | deployment `cost` |
| model `limit` | deployment `limits` |

The release id is `family/modelID@revision`; the deployment id is
`provider/model-key`. A second provider serving the same release gets a second
deployment, as the gate already expects.

Only OpenAI-compatible packages are considered. A literal `apiKey` or
authorization header is never copied; a provider that has no environment
variable name is skipped with a reason. The role policy is separate because
independence is a maintainer decision:

```json
{
  "proposers": [
    "opencode/deepseek-v4.1-flash",
    "opencode/qwen3.8-27b"
  ],
  "judge": "opencode/glm-5.3"
}
```

The importer supports V2 `providers` and legacy `provider`. JSONC is normalised
by a small local parser that removes comments and trailing commas outside
strings; malformed input is rejected rather than guessed.

A normal import preserves `thresholds`, `quantization`, `prompt_hash`,
`decoding` and unknown top-level keys. `--force` replaces the deployment
fields. The result is validated by the existing `load_config` before it is
written, and `--dry-run` prints the diff without writing.

Alternatives considered: auto-selecting the two proposers and judge by family
order. Rejected because provider cost, reliability and availability are
maintainer decisions, and a silent role change would alter the gate's
independence evidence.

### 9. Prices are data, not policy

The cost report and budget are advisory. A high price does not demote a model
and a low price does not qualify one. Qualification, conformance, drift and
defect rate remain the quality gates. This keeps the approval contract stable
and lets a maintainer trade cost against quality explicitly.

## Risks / Trade-offs

- **A heuristic estimate can be wrong** → label it as an estimate, report a
  range, record the heuristic, and treat provider usage as authoritative.
- **Prices go stale** → sync from OpenCode on demand; the report shows the
  price source and the date the config was generated.
- **A provider omits usage** → record unknown cost, never zero; the report
  lists it so the model cannot look artificially cheap.
- **Cached-token accounting varies by provider** → accept the common field
  names and record the raw usage object for audit.
- **`gate_runs` grows the ledger** → it is optional and maintainer-written;
  the report can filter by date, and a future change can add retention.
- **OpenCode priority can change** → the importer resolves a single config or
  an explicit `--opencode` path; it does not silently merge ancestors.
- **A literal secret in OpenCode** → the importer never reads values, skips a
  provider without an env name, and tests assert no literal key is copied.
- **More than one provider serves one release** → release identity stays
  shared and costs are compared per deployment.
- **A cheap model may be cheap because it abstains** → the report includes
  abstentions and cost per approval, not just total spend.

## Migration Plan

- Existing gate configs load unchanged; `cost` and `limits` are optional.
- The importer can generate a new config or merge into an existing one.
  `--dry-run` is the default review step; `--force` is explicit.
- Existing ledgers need no rewrite; `gate_runs` is optional and appears on the
  next recorded action.
- Re-run `dev/translation_gate.py validate` after a sync.
- No runtime application behavior changes and no release-path behavior
  changes.

## Open Questions

- Whether to add retention or rotation for `gate_runs` can wait until the
  ledger size becomes a problem; it does not change the specs or approach.
- The first real corpus may show that the default `chars_per_token` needs
  calibration; it is configurable and does not change the contract.
