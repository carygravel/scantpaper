# Tasks

## 1. Deployment headers

- [x] 1.1 Add optional `headers` to the deployment schema and loader, reject
  non-string values, and verify an existing config without headers still
  loads.
- [x] 1.2 Send deployment headers from the OpenAI-compatible client, with the
  authorization header kept separate, and verify a mocked request includes the
  configured metadata header.

## 2. Tiered prices

- [x] 2.1 Add optional context tiers to the deployment cost schema and loader,
  validate non-negative context sizes and prices, and verify a config without
  tiers keeps the current behavior.
- [x] 2.2 Select the base or highest applicable tier from the prompt token
  count, record the chosen tier with the call, and verify base, tiered and
  missing-tier-price cases.

## 3. Running-catalog import

- [x] 3.1 Add `--from-api` to the sync command, invoking `opencode api get
  /api/model`, `/api/provider` and `/api/integration/<id>`, and verify a
  missing or unreadable response writes nothing.
- [x] 3.2 Add saved-response inputs for models, providers and integrations,
  and verify the same catalog imports offline without a running server.
- [x] 3.3 Map provider/model identity, family, release date, base URL, cost,
  limits and headers; verify default `opencode` models and a non-compatible
  package are handled correctly.
- [x] 3.4 Resolve `key_env` from the integration environment method, skip an
  OAuth-only provider, and verify an explicit `--key-env` override without
  copying a secret.
- [x] 3.5 Preserve local thresholds and manual fields, keep the real config and
  roles git-ignored, and verify a second import is deterministic and
  `--dry-run` writes nothing.

## 4. Documentation and examples

- [x] 4.1 Document `--from-api`, saved-response inputs, the API source of
  default models, the OAuth limitation, the package filter and the headers
  rule in `po/README.md`.
- [x] 4.2 Add or update generic example configs with a `headers` field and a
  cost tier, and verify they load with `dev/translation_gate.py validate`.

## 5. Integration verification

- [x] 5.1 Run `pytest`, `python3 dev/check_test_coverage.py`,
  `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_po.py` and
  `openspec validate --specs --strict --no-interactive`; verify no new
  uncovered lines, partial branches, lint, type or catalog errors.

## Workflow follow-up

- Archive the change after review and verify the archived result.
