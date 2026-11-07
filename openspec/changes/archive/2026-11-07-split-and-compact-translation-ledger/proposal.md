# Proposal

## Why

`po/translation-approvals.json` is 5.6 MB and 178,291 lines. The approvals
are 4.2 MB of that, and each gate approval carries the full proposal, check
and call payloads. The recent en_GB batch added about 29,000 lines for 100
approvals. Every future batch grows the same file, and every language edit
competes for the same file in git.

The evidence payload is the bulk, not the number of approvals. A language-level
split fixes the merge conflicts; moving the full evidence to a sidecar fixes
the size.

## What Changes

- Replace the single ledger with a small manifest and one file per language:

  ```text
  po/approvals/manifest.json
  po/approvals/en_GB.json
  po/approvals/de.json
  ...
  ```

- Keep approvals, qualifications, conformances, revocations, false positives,
  drift excursions and audit samples in the language file. Keep compact gate
  run summaries there too.
- Move the full evidence - proposal texts, judge verdict details, check
  results, calls, token usage and latency - to a content-addressed,
  git-ignored sidecar. Each approval and operational record keeps an
  `evidence_sha256` plus a compact summary.
- Add a loader that merges the per-language files for the release build,
  audit and cost report. `gate` and `translate` write only the language file
  they changed.
- Add a one-time migration that splits the current ledger, writes the sidecar
  for the existing evidence, and verifies that every approval key and
  translation hash survives.
- Document the layout, the sidecar retention rule and the release path.

Out of scope: changing approval criteria, provenance classes or gate
decisions; committing the sidecar; deleting the old ledger from git history.
The sidecar becomes an audit/CI artifact, not a release dependency.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: an approval may record an evidence digest and
  compact summary, with the full evidence retrievable from a
  content-addressed store.

## Impact

- `po/translation-approvals.json`: replaced by `po/approvals/` after
  migration.
- `.gitignore`: ignores the evidence sidecar.
- `dev/translation_ledger.py`: split-loader/writer, evidence store and
  compact records.
- `dev/translation_gate.py`: language-file writes and sidecar evidence.
- `dev/compile_mo.py`, `dev/audit_human_core.py`: read the merged view.
- `dev/tests/test_translation_ledger.py`, `test_translation_gate.py`,
  `test_audit_human_core.py`: split, evidence and migration tests.
- `po/README.md`: layout, retention and migration documentation.
- No shipped `scantpaper` change and no new dependency.
