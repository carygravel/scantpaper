# Design

## Context

See `proposal.md` for motivation. The existing sync tool reads an OpenCode
JSON/JSONC file, so it only sees providers the user explicitly added. The
running OpenCode server exposes the resolved catalog at `/api/model` and
`/api/provider`; `/api/integration/<id>` supplies the credential method names.
The gate client currently sends only `Authorization`, and the gate config
stores one price per token category.

## Goals / Non-Goals

**Goals:**

- Import the resolved default catalog without reading private provider config.
- Resolve credentials by environment variable name, never by value.
- Support the provider metadata headers that default providers require.
- Cost tiered models correctly.
- Keep the real gate config and roles local and git-ignored.

**Non-Goals:**

- No OAuth token extraction or reuse of OpenCode's credential store.
- No OpenAI Responses or native-provider transport.
- No automatic proposer/judge selection.
- No committed provider-specific config.

## Decisions

### 1. Use the local OpenCode API through the `opencode api` CLI

`--from-api` invokes:

```sh
opencode api get /api/model
opencode api get /api/provider
opencode api get /api/integration/<integrationID>
```

The CLI owns server discovery and local authorization, so the sync does not
need an HTTP client, a port or an OpenCode token. The JSON payloads are the
same ones the UI uses.

Saved responses are accepted through `--models-json`, `--providers-json` and
`--integrations-json <dir>` for tests and offline review. These are also the
fixtures used in the test suite.

Alternatives considered: calling `opencode models` (IDs only, no prices or
base URLs), the models.dev API (no resolved base URL, headers or integration
methods), and direct HTTP to the server (duplicates discovery and auth).

### 2. The API source is additive, not a replacement

`--from-api` is mutually exclusive with the config-file source in one run.
The existing `--opencode` path stays unchanged. Both write the same local,
git-ignored `${output}` and use the same role policy and merge rules.

The API source includes built-in and configured providers because the server
has already resolved both. A `--provider` filter can narrow the import; the
role policy still controls which deployments propose or judge.

### 3. Only OpenAI-compatible chat packages are imported

The gate client posts to `/chat/completions`, so a model is imported only when
its package is an OpenAI-compatible chat package. Responses/native packages
are skipped with a reason. The default `opencode` provider has both kinds; the
default `deepseek`, `qwen` and `glm` entries use the compatible package, while
some GPT/Claude entries use a native package.

### 4. Credentials come from integration methods

The provider's `integrationID` is resolved through `/api/integration/<id>`.
The first declared environment method supplies `key_env`; the value is never
read. A provider with only OAuth is skipped unless the caller passes
`--key-env provider=ENV`. This makes the OAuth limitation explicit instead of
silently generating a config that cannot authenticate.

The default `opencode` integration declares `OPENCODE_API_KEY`, an API-key
method and an OAuth device method. The gate can use the key variable; it
cannot reuse an OAuth connection.

### 5. Provider headers are local deployment data

A deployment gains optional `headers`. The sync copies provider and model
headers into the local config, with model values overriding provider values.
`Authorization`, `Proxy-Authorization` and cookie headers are never copied.
The client sends the remaining headers with every request.

The default `opencode` provider sends `x-opencode-org-id`. Keeping that header
in the local config avoids committing provider identity while letting the gate
talk to the same endpoint as OpenCode.

### 6. Prices support a base rate and context tiers

The deployment `cost` object keeps the existing base fields and gains an
optional `tiers` list:

```json
"cost": {
  "currency": "USD",
  "unit": "per_million_tokens",
  "input": 2.0,
  "output": 10.0,
  "cache_read": 0.1,
  "cache_write": 2.5,
  "tiers": [
    {
      "context": 272000,
      "input": 4.0,
      "output": 15.0,
      "cache_read": 0.2,
      "cache_write": 5.0
    }
  ]
}
```

At cost time, the gate chooses the tier with the largest `context` not
exceeding the prompt token count. The base rate applies below the first tier.
The selected tier is recorded with the call so the report and audit show which
price was applied.

The OpenCode catalog's first cost entry is the base. Each later entry has
`tier.type: "context"` and `tier.size`; it maps to one tier.

### 7. Release and deployment identities stay stable

A release id is `family/modelID@YYYY-MM-DD`; the revision comes from
`time.released` epoch milliseconds. If the release time is zero or absent, the
revision is a short hash of the model id. A deployment id is
`providerID/modelID`. This keeps the two-level identity while allowing two
providers to serve the same release.

### 8. Local-only files and committed examples

The real `po/translation-gate.json` and `po/translation-gate.roles.json` stay
in `.gitignore`. The committed `*.example.json` files are generic fallbacks
for a clean checkout and for validation. `--from-api` writes only the local
files unless the caller explicitly chooses another output.

## Risks / Trade-offs

- **The OpenCode API is experimental** → validate every payload and write
  nothing on a schema mismatch; fixtures pin the accepted shapes.
- **Provider headers may be sensitive** → copy only non-auth metadata headers,
  keep the config local, and never print a header value in errors.
- **OAuth users cannot run the gate directly** → require an API key variable
  or a proxy; report the OAuth-only case explicitly.
- **Tier data is incomplete** → record the selected tier and unknown cost
  rather than guessing.
- **A model's package changes** → the package filter may drop it; report why.
- **Zero-price/free models** → keep zero prices distinctly from missing
  prices, so free is not confused with unknown.
- **The catalog is large** → use `--provider` to narrow; roles still select
  the active deployments.

## Migration Plan

- Existing config files load unchanged; `headers` and `cost.tiers` are
  optional.
- The config-file source keeps its current behavior; `--from-api` is additive.
- Regenerate the local config with `--from-api --dry-run`, review, then write.
- Re-run `dev/translation_gate.py validate` after an import.
- No release-path behavior changes.

## Open Questions

- Whether to add an OpenAI Responses transport or an OpenCode proxy adapter is
  a separate change; it does not affect this API source.
- Whether to support OAuth tokens from the OpenCode credential store is a
  separate security decision; this design deliberately refuses it.
