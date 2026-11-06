# Proposal

## Why

`opencode.jsonc` lists only providers added by the user. The default OpenCode
models live in the running server's resolved catalog, so the current sync tool
never sees them. That leaves the gate without the model families, limits and
prices that OpenCode already knows. The server API exposes the missing data,
including the default `opencode` provider, but the gate cannot yet import or
authenticate against it.

The gate config is intentionally local and git-ignored because it can name
private providers. Importing the running catalog should preserve that rule:
write the local config, never copy a credential, and keep only generic
examples in git.

## What Changes

- Add a `--from-api` source to `dev/sync_translation_gate.py`. It reads the
  resolved catalog from `opencode api get /api/model` and
  `/api/provider`, and reads credential method names from
  `/api/integration/<id>`.
- Map provider and model identity, base URL, release date, token limits,
  prices and provider headers into the local gate config.
- Resolve `key_env` from the integration's environment method. Skip a provider
  that only offers OAuth unless an explicit `--key-env` override is supplied.
- Import only OpenAI-compatible chat packages. Exclude Responses/native
  packages that the current client cannot call.
- Add optional deployment `headers` and send them from the gate client, so the
  default `opencode` provider's `x-opencode-org-id` can be carried locally.
- Add tiered prices to the deployment cost model and choose the tier from the
  prompt token count, so default OpenCode models with context tiers are costed
  correctly.
- Support saved API responses as input for tests and offline review, without a
  running server.
- Document the API source, the OAuth limitation, the package filter, the local
  config rule and the new fields in `po/README.md`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `translation-gate-costing`: adds a running OpenCode catalog as an import
  source, provider headers, integration-derived credentials, OpenAI-compatible
  package filtering, and tiered prices.

## Impact

- **Tooling:** `dev/sync_translation_gate.py`; `dev/translation_gate.py` for
  headers, tiered cost calculation and the new source; tests under `dev/tests/`.
- **Configuration:** `po/translation-gate.json` gains optional `headers` and
  `cost.tiers`; the real file stays git-ignored. Generic examples remain
  committed.
- **Provider API:** reads the local OpenCode HTTP API through the `opencode
  api` CLI; no direct network client is added.
- **Dependencies:** none. The importer does not add an OpenCode SDK or a new
  HTTP client.
- **Security:** only environment variable names and non-secret provider
  metadata are copied. OAuth tokens, API keys and authorization headers are
  never read or written.
- **Non-goals:** no OAuth token extraction, no OpenAI Responses transport, no
  automatic proposer/judge selection, and no commit of the real gate config.
