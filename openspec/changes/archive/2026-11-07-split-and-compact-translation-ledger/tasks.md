# Tasks

## 1. Storage model

- [x] 1.1 Add `po/approvals/manifest.json`, `global.json` and per-language
  file schemas, with `language` and cross-file duplicate-key validation.
- [x] 1.2 Extend `translation_ledger.py` with a merged directory loader, a
  language-scoped loader/writer, a global writer and manifest handling while
  keeping single-file loading for legacy tests and checkouts; verify round
  trips, duplicate rejection and legacy compatibility.
- [x] 1.3 Update the default ledger path and the `--ledger`/`--approvals`
  options to accept either a directory or a single file; verify `validate`,
  `compile_mo` and `audit_human_core` on both forms.

## 2. Evidence sidecar

- [x] 2.1 Add canonical hashing, append-only NDJSON storage, deduplication and
  lookup for the sidecar, with a configurable `--evidence` path; verify hashes,
  duplicate payloads and missing-store reporting.
- [x] 2.2 Replace full approval evidence, qualification calls, drift calls and
  gate-run calls with compact summaries plus `evidence_sha256`; preserve the
  fields used by `costs`, audit and release; verify a compact record still
  validates and resolves through the sidecar.

## 3. Tool integration

- [x] 3.1 Make `gate`, `translate`, `approve` and the qualification/drift
  commands write only the affected language file and the sidecar, while
  `revoke` writes the global file; verify other language files are unchanged.
- [x] 3.2 Make `compile_mo`, `audit_human_core` and `costs` read the merged
  view and use summaries when the sidecar is absent; verify a fresh checkout
  can build a release and still reports cost totals.

## 4. Migration

- [x] 4.1 Add `dev/split_translation_ledger.py` with a dry-run and write mode;
  verify approval counts, keys, translation hashes, evidence hashes and
  idempotence against the current ledger.
- [x] 4.2 Run the migration on a copy, inspect the new tree and sidecar,
  remove the old ledger only after verification, and document the sidecar
  archive step in `po/README.md`; verify the release and audit commands on the
  migrated tree.

## 5. Integration verification

- [x] 5.1 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate split-and-compact-translation-ledger --strict
  --no-interactive`; verify all pass and coverage does not regress.

## Workflow follow-up

- Archive the change after review.
- Keep the old ledger blob in git history; do not rewrite history.
