# Design

## Context

See `proposal.md` for motivation and `specs/` for the behavior contract. The
relevant current state:

- `dev/generate_pot.py` builds the template; `dev/summarise_po.py` reports
  each catalog's own counts; `dev/check_po.py` validates catalogs and source
  strings; `dev/compile_mo.py` compiles with polib, which drops fuzzy entries.
- Rosetta layout is `po/scantpaper/<lang>.po` beside `scantpaper.pot`; the
  pre-2026 human reference is git commit `1a303718`.
- `dev/rosetta_tarball.py` packages the directory for upload, but nothing
  downloads an export. Launchpad export is a logged-in, one-off web request.
- The installed system catalogs are the only cross-project corpus already
  available locally; there is no committed translation memory.
- Developer tooling tests live in `dev/tests/` and `src/scantpaper/tests/`.
  The 99% coverage gate covers the shipped package only.

## Goals / Non-Goals

**Goals:**

- Make approval state explicit, reviewable and independent of the fuzzy flag.
- Make every automated step reproducible from committed inputs plus an
  optional local corpus.
- Keep the release path offline and deterministic.
- Bound the blast radius of a bad model or a bad corpus to one language or
  one provenance class.

**Non-Goals:**

- No runtime behavior change and no new analysis about how strings are used.
- No automated Launchpad export client in this change.
- No committed translation-memory database.
- No requirement that every language reach full coverage.

## Decisions

### 1. The ledger is a separate JSON document, not `.po` comments

Store approvals in `po/translation-approvals.json`, with one record per
approved translation and a top-level `version` and `snapshot` field. The
catalog stays standard gettext, so external tools keep working and a `.po`
diff never mixes approval metadata with translations.

Alternatives considered: `#` comments beside each entry (fragile through
`msgmerge`, invisible to gettext tooling), and SQLite (opaque in review).
JSON is diffable and needs no dependency.

### 2. An approval is keyed by content, not by position

Each record carries `language`, `msgctxt`, `msgid`, `msgid_plural`, a
`translation_sha256`, and the stored translation. The digest covers the
canonical serialization of `msgstr` or every plural form, including
whitespace. Lookup is by the full tuple, so editing a translation or a source
string cannot inherit an old approval.

A digest rather than the raw text as the key keeps the index small and avoids
duplicate-key ambiguity for multiline and plural entries. The raw text is
still stored for audit and for a readable diff.

Alternatives considered: approval recorded only as "msgid approved" (a
translation edit would silently keep the approval) and a per-catalog sidecar
keyed by line number (breaks on every merge).

### 3. The frozen human core is the git commit, not a duplicate tree

The audited reference is commit `1a303718`, read with `git show`. The ledger
records that hash in its `snapshot` field. A duplicate `po/human-core/` tree
was rejected: it doubles the catalog payload, drifts on merge, and would need
its own validation.

Tooling that must work outside a git checkout (a source tarball) reports the
snapshot as unavailable and refuses to make historical-approval decisions;
it does not guess. The release path never needs the snapshot.

### 4. Translation memory is a local SQLite index with a committed manifest

`dev/tm_index.py` builds `.cache/translation-memory.sqlite3` from:

- the installed `/usr/share/locale/*/LC_MESSAGES/*.mo` catalogs, and
- optional upstream or Ubuntu language-pack `.po` trees passed on the command
  line.

The index is git-ignored and reproducible. A committed
`po/tm-sources.json` manifest records each source's project, language,
licence and origin, so the index's inputs are reviewable without committing
the corpus. Tables:

```
sources(id, project, language, license, origin, imported_at)
entries(source_id, language, source_norm, target, target_norm)
```

`source_norm` is the mnemonic-stripped, whitespace-collapsed, NFKD-folded,
case-folded source. Dominance is computed over distinct source projects, not
raw occurrences, so one large catalog cannot outvote the corpus.

Alternatives considered: a committed compressed JSONL corpus (licensing and
size review burden) and querying installed `.mo` files on every run (slow and
not reproducible across machines).

### 5. Fuzzy entries are checked, with a ratchet for the existing backlog

`dev/check_po.py` validates every non-obsolete entry, fuzzy included. Empty
fuzzy entries are skipped because there is no text to check. Because the
current fuzzy backlog contains known defects (the `hi`/`tr` plural `%`
errors), the first release records the existing violations in
`po/fuzzy-defect-baseline.json` keyed by catalog, msgid and check. The check
reports all violations and fails only on a violation absent from the baseline;
fixing one removes it from the baseline. This is a ratchet, not a disabled
check, and an entry with a baselined defect cannot be approved.

Alternatives considered: enforcing immediately (blocks unrelated work on
hundreds of pre-existing entries) and leaving fuzzy entries unchecked
(violates the spec and hides exactly the defects that approval would ship).

### 6. The render check compiles a de-fuzzed temporary catalog

A pytest check copies each catalog to a temporary directory, clears the fuzzy
flag, compiles it with `msgfmt` (or polib), and formats every message with
arguments generated from its placeholders. It uses the real gettext lookup
path, so a `%` or `{}` mismatch raises before approval. The temporary copy is
never written into `po/`.

Alternatives considered: formatting `msgstr` directly (does not exercise
plural selection or catalog compilation) and adding a runtime check (ships
the fault to users first).

### 7. Model access is an adapter configured in JSON

`po/translation-gate.json` separates model releases from deployments. A
release is `family + model id + revision`. A deployment adds provider,
endpoint, quantization, prompt-template hash and decoding parameters, and
names the release it serves. Secrets are never in the file.

The gate refuses to run if the proposer families are not distinct, if the
judge family matches either proposer, or if two deployments of one release
are offered as the two independent voices. JSON rather than TOML because the
project supports Python 3.10, where `tomllib` is unavailable; `tomli` is a
test dependency, not a runtime one.

### 8. Release filtering lives in `compile_mo.py`

`dev/compile_mo.py` gains `--approvals PATH`. When given, it loads the ledger,
drops any entry without a matching valid approval, and then compiles. Without
the option it keeps today's behavior, so existing tests and local previews are
unaffected. Packaging and release automation pass the ledger explicitly.

Filtering at compile time rather than in the packaging scripts keeps one
implementation and makes the fallback observable in the compile report
(per-language counts of dropped entries).

### 9. Rosetta export stays manual in this change

Launchpad has no bulk export API and no API key: export is a logged-in web
request whose result arrives as an expiring link. Implementing OAuth, a form
POST and email retrieval is disproportionate and fragile. Instead:

- `dev/rosetta_import.py` validates and merges a `.po` or language-pack tree
  the maintainer has downloaded.
- The README documents the export URL and the read-only OAuth option for
  anyone who wants to automate it later with `launchpadlib`.

This satisfies the spec's MAY: no credential is required, and CI never
authenticates. The token question is therefore not on the critical path.

### 10. Merge uses `msgmerge --previous` plus explicit post-processing

`dev/merge_po.py` regenerates the template and runs
`msgmerge --previous --no-fuzzy-matching` per catalog. `--previous` records
the old msgid as `#| msgid`, which is the audit trail for a changed source
string; `--no-fuzzy-matching` prevents gettext from inventing a fuzzy
translation. Post-processing keeps existing fuzzy flags, preserves the
pre-2026 entry text, and normalizes the header dates so an unchanged catalog
produces no diff.

The previous msgid is also copied into the ledger's audit record when an
entry changes, because `#|` comments can be dropped by later tooling.

### 11. Coverage is a new mode of `summarise_po.py`

`dev/summarise_po.py --pot po/scantpaper/scantpaper.pot` reports shipped,
fuzzy, missing, stale and obsolete against the template; without `--pot` it
keeps the current per-catalog view. `--json` supports tests and the release
report. One implementation avoids the current situation where two reports
disagree about coverage.

### 12. Model-changed entries default to the human text

`dev/audit_human_core.py` compares each current non-fuzzy entry with commit
`1a303718`:

- identical: import as `human-historical`;
- different, and the current text passes every deterministic check while the
  old text fails one: keep the current text, but classify it as
  `machine-strong` only after the gate approves it;
- different otherwise: restore the pre-2026 text as `human-historical` and
  park the model variant as a fuzzy proposal.

This makes the safe outcome the default and turns a model rewrite into an
explicit proposal rather than a silent grandfather. The 2,240 model-added
entries have no human text to restore and go through the gate directly.

### 13. High-impact classification is a shared dev policy module

`dev/translation_policy.py` owns `HIGH_IMPACT_ACTION_WORDS`, the length bound,
the occurrence rules (`.ui` widgets and `dialog/`) and
`is_high_impact(msgid, occurrences)`. Both the gate and the tests import it,
so the definition cannot drift between the proposal, the tests and the
implementation.

### 14. Batch commands are per-language, resumable and offline-first

Model and TM commands process one language at a time, write results after
each language, and accept `--language` to resume. They print a progress line
per language and exit non-zero only on an unreadable input or an inconsistent
ledger, not on abstentions. No GUI thread, cancellation or progress-bar
machinery is involved; these are maintainer-run developer tools.

### 15. Qualification attaches to a release; conformance to a deployment

The ledger keys a qualification by `(release, language)` and a conformance by
`(deployment, release)`. Full qualification runs once per release and
language. A new deployment of an already-qualified release is admitted by
conformance: it declares an exact release identity and an equivalent serving
configuration, then passes the release's drift probe. A deployment id is the
hash of its provider, endpoint, quantization, prompt hash and decoding
parameters, so any configuration change produces a new deployment and
requires conformance again.

Only an exact release identity can inherit. A re-quantized variant, fine-tune
or version that cannot be tied to a qualified release is a different model
and needs full qualification. Every approval records both the release and the
deployment, which is what makes deployment-scoped and release-scoped
revocation possible. Retiring either keeps the approvals; it only removes a
future path.

### 16. Drift probes and the capability report

`po/drift-probe/<lang>.json` holds a fixed, versioned set of 30-50
human-translated strings per language, stratified across short labels,
sentences, placeholders, plurals and high-impact actions. It is disjoint from
the full qualification set. The release's qualification records the probe
baseline; each batch re-runs the probe for the languages it touches.

The alarm margin must account for the sample size, so a 30-50 item probe
pauses approvals rather than demoting anything. On an alarm the gate stops
new approvals for that release and language, re-qualifies, and marks
approvals produced since the last good probe for audit. Only confirmed
defects are demoted.

The capability report is the other half: it lists, per language, which
releases and deployments are currently qualified. A language with none is
reported as having no machine path for new strings; its existing
translations, including those from a retired model, are not flagged.

## Risks / Trade-offs

- **A ledger and a catalog can disagree** → validation rejects an approval
  whose digest, language or context does not match an entry, and the release
  filter treats it as absent. The ledger never overrides a malformed catalog.
- **The 1,467-entry audit may restore a genuine improvement** → the model
  variant is kept as a fuzzy proposal, so no work is lost; a reviewer can
  approve it later.
- **Fuzzy-defect baselines can hide a regression** → the baseline is keyed by
  exact check and msgid, is reported in full on every run, and can only
  shrink; new defects fail CI.
- **Model families may share training data and fail together** → a different
  judge family, back-translation, a TM cross-check and the audit sample are
  independent signals, but none is proof. The provisional class and the kill
  switch bound the damage.
- **Two providers of one release may look independent** → identity is
  release-based; an equal release counts as one family even across providers.
- **A provider may change a model behind a stable id** → the probe compares
  the deployment with its release baseline, pauses new approvals on a drop,
  and forces re-qualification; it does not demote existing work on its own.
- **A model may be retired** → its approvals remain shipped and auditable; the
  capability report names the languages that lose a future machine path.
- **Translation-memory licensing is easy to get wrong** → the manifest
  records a licence per source; ingestion refuses a source with no licence or
  an incompatible one. Individual Rosetta strings are BSD, but a project
  catalog is not assumed to be.
- **Launchpad's template is stale (544 vs 665)** → the sync imports only what
  the export contains and never treats Rosetta as the source of the newest
  strings. The local template remains authoritative.
- **The local TM is not available in CI** → CI runs deterministic checks
  only; a missing index is reported, never silently treated as "no match".

## Migration Plan

1. **Import the human core.** Build the ledger from `1a303718`; audit the
   model-added and model-changed entries. Non-fuzzy entries without an
   approval are reported but still ship until step 3.
2. **Turn on the checks.** Validate fuzzy entries, add the render check and
   the defect baseline, and land the coverage report. CI stays green because
   no release behavior has changed yet.
3. **Turn on the release filter.** Add `--approvals` to the release and
   packaging path. Every shipped entry now has a ledger record; the first
   release report names any accidental fallback.
4. **Run the first refresh.** Build the TM index, qualify model releases,
   conform deployments, and gate a small language set. Expand only after the
   drift probe and the audit sample are acceptable.

Rollback: steps 2 and 3 are independent. Removing `--approvals` restores the
previous compile behavior immediately; the ledger and index are inert data
files. Catalog changes from a merge are ordinary git history, so a bad merge
is reverted like any other commit.

## Open Questions

- The initial qualification, conformance, drift, TM-dominance and defect-rate
  thresholds need calibration on the first real corpus. Defaults are recorded
  in `po/translation-gate.json` and can be tuned in a follow-up PR without
  changing the specs, the approach or the task order.
