# Design

## Context

See `proposal.md` - Why.

The current ledger is one JSON document with `approvals`, `qualifications`,
`conformances`, `revocations`, `false_positives`, `drift_excursions`,
`audit_samples` and `gate_runs`. The approvals and their full evidence are
the bulk; the calls inside gate runs, qualifications and drift probes add
operational detail.

`dev/translation_ledger.py` owns loading, validation and writing. Callers are
`translation_gate.py`, `compile_mo.py`, `audit_human_core.py` and their tests.
The release build only needs approvals; the cost and audit tools need the
operational detail.

## Goals / Non-Goals

**Goals:**

- Keep the committed ledger small and reviewable.
- Avoid one large file shared by every language.
- Preserve every approval, translation hash and provenance class.
- Keep release builds independent of the evidence sidecar.
- Keep cost and audit detail available locally or in CI.

**Non-Goals:**

- Changing the gate's approval criteria or provenance classes.
- Committing the evidence sidecar.
- Rewriting git history to remove the old ledger blob.
- Changing the release gate's approval semantics.

## Decisions

### Directory layout

```text
po/approvals/
  manifest.json      version, snapshot, language list
  global.json        conformances, revocations
  en_GB.json         language approvals and language-level sections
  de.json
  ...
```

The per-language file contains:

```text
version, snapshot, language
approvals, qualifications, false_positives,
drift_excursions, audit_samples, gate_runs
```

`conformances` and `revocations` stay in `global.json` because a deployment or
release revocation spans languages. `qualifications` stay with their language;
`conformances` are release/deployment facts and are global.

### Compact records

Approvals keep their identity, provenance, model release, deployment, date,
`translation_sha256`, and an `evidence` summary:

```json
"evidence": {
  "sha256": "…",
  "judge": {"deployment": "…", "verdict": "…", "tie": false},
  "proposals": [{"deployment": "…", "family": "…"}],
  "checks": {"deployment": []},
  "backtranslation": true,
  "high_impact": false,
  "prompt_version": 1,
  "prompt_hash": "sha256:…"
}
```

The full evidence, including proposal texts and calls, is addressed by
`sha256`. Qualifications, drift excursions and gate runs keep their scores,
costs, counts and hashes but not their call arrays.

### Evidence sidecar

The sidecar is append-only NDJSON at `.cache/translation-evidence.ndjson`
(configurable with `--evidence`):

```json
{"sha256":"…","kind":"approval","language":"en_GB","payload":{…}}
```

The hash is the SHA-256 of the canonical JSON payload (sorted keys, compact
separators). Duplicate payloads are written once. The sidecar is git-ignored;
CI archives it with the release artifacts. If it is missing, approvals still
validate and ship; audit and detailed cost reports report the evidence as
unavailable.

### Loader and writer

`translation_ledger.py` gains:

- `load_ledger(path)`: accepts a single file (legacy) or the approvals
  directory and returns the merged view.
- `load_language_ledger(directory, language)` and
  `write_language_ledger(data, directory, language)` for gate and batch writes.
- `write_global_ledger` for conformances and revocations.
- `write_evidence` / `load_evidence` for the sidecar.

`translation_gate.py` uses the language-scoped loader/writer. `approve` takes
the language from the decision record. `revoke` writes `global.json`. The
merged loader is used by `compile_mo.py`, `audit_human_core.py` and `costs`.

### Release path

`compile_mo.py` and the release gate read approvals from the merged
per-language files. They do not read the sidecar. A fresh checkout with the
committed approvals can build a release even if the evidence sidecar was never
downloaded.

### Cost and audit paths

The cost report uses the committed summaries for totals and the sidecar for
per-deployment call detail. The audit resolves approval and run hashes from the
sidecar; a missing sidecar is reported, not treated as a validation failure.
The migration writes the sidecar for the historical records; the old ledger
remains in git history as a fallback.

### Migration

`dev/split_translation_ledger.py` reads the current ledger and writes the new
tree plus the sidecar. Before removing the old file it verifies:

- every approval key and `translation_sha256` survives;
- approval counts per language match;
- every evidence hash resolves in the sidecar;
- the merged loader produces the same approval set as the old ledger;
- a second migration run is a no-op.

The migration is a one-time, reviewable commit. The old file remains in git
history; the sidecar is archived by CI.

## Risks / Trade-offs

- **Sidecar loss** -> approvals still ship, but audit detail is unavailable.
  Mitigate with CI artifacts and the old ledger in history.
- **Compact evidence** -> the summary is not the full audit trail. The digest
  and sidecar are required for a deep audit; the spec allows the report to say
  the evidence is unavailable.
- **Migration mistakes** -> the script verifies counts, keys and hashes before
  removing the old file; run it on a branch.
- **Global sections** -> conformances and revocations can conflict in one
  small file. They change rarely; the manifest and global file stay small.
- **Fresh checkout without sidecar** -> `costs` shows summaries rather than
  per-call detail. This is acceptable for maintainer tooling; the release path
  is unaffected.
- **Git history size** -> the old 5.6 MB blob remains in history. Rewriting
  history is out of scope; the change controls future growth.

## Migration Plan

1. Add the directory loader/writer and sidecar support with tests.
2. Run the migration on a branch and verify the old/new approval sets.
3. Commit the split files, the sidecar retention documentation and the
   removal of the old ledger.
4. Archive the sidecar with the release artifacts.
5. Roll back by restoring `po/translation-approvals.json` from git and
   reverting the tooling change; approvals are unchanged.

## Open Questions

None.
