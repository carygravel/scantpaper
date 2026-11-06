# Tasks

## 1. Ledger and policy foundation

- [x] 1.1 Add `dev/translation_policy.py` with the six provenance classes,
  the high-impact action words and `is_high_impact(msgid, occurrences)`;
  verify `pytest dev/tests/test_translation_policy.py` covers a menu action,
  a destructive verb, a tooltip and a `dialog/` occurrence.
- [x] 1.2 Add `po/translation-approvals.json` with `version`, `snapshot` and
  an empty `approvals` list, plus load/validate helpers that reject an unknown
  class or a missing digest; verify the schema tests cover both rejections.
- [x] 1.3 Add ledger-to-catalog validation: a record whose language, context,
  msgid or translation digest does not match an active entry is reported and
  cannot approve it; verify a mutated `msgstr` makes the approval invalid.
- [x] 1.4 Document the ledger key, the six classes and the difference between
  an approval and a fuzzy flag in `po/README.md`; verify the
  documented example round-trips through the helpers.

## 2. Recover and audit the human core

- [x] 2.1 Add `dev/audit_human_core.py` to read commit `1a303718` with
  `git show` and classify every current non-fuzzy entry as unchanged,
  model-changed or model-added; verify the tests use a temporary git
  repository and cover all three classes.
- [x] 2.2 Implement the audit policy: keep an unchanged entry as
  `human-historical`; keep a model change only when it fixes a deterministic
  defect and the gate approves it; otherwise restore the pre-2026 text and
  park the model variant as fuzzy; verify each branch with a fixture.
- [x] 2.3 Run the audit over `po/scantpaper/*.po`, commit the populated
  ledger and the audit report, and verify that every shipped entry either has
  a record or is listed in the report as pending.
- [x] 2.4 Verify the committed counts against the pre-2026 snapshot: the
  report must account for all 13,615 shipped entries, including the 2,240
  model-added and 1,467 model-changed ones, without silently grandfathering
  either group.

## 3. Validate fuzzy proposals and rendered messages

- [x] 3.1 Extend `dev/check_po.py` to validate every non-obsolete entry,
  fuzzy included, while skipping entries with no text; verify existing tests
  still pass and a fuzzy entry with a bad placeholder now fails.
- [x] 3.2 Add `po/fuzzy-defect-baseline.json` and the ratchet: report every
  violation, fail only on one absent from the baseline, and allow the
  baseline to shrink; verify a new defect fails and a fixed one can be
  removed.
- [x] 3.3 Add a test-only render check that copies catalogs, clears fuzzy,
  compiles them and formats every message with generated arguments; verify it
  catches a `%` mismatch and a renamed `{}` field.
- [x] 3.4 Fix the known `hi`/`tr` plural format defects, remove them from the
  baseline, and verify the render check and `dev/check_po.py` both pass.

## 4. Coverage, merge and release filtering

- [x] 4.1 Add `--pot` and `--json` to `dev/summarise_po.py`; verify a
  fixture with 549 shipped entries in a 558-entry catalog and a 665-msgid
  template reports 549 of 665, plus separate missing and stale counts.
- [x] 4.2 Add `dev/merge_po.py` using `msgmerge --previous
  --no-fuzzy-matching`, preserving fuzzy flags, the snapshot and previous
  msgid; verify a second run on unchanged inputs produces no diff and a
  changed msgid records its predecessor.
- [x] 4.3 Add `--approvals PATH` to `dev/compile_mo.py`; verify an approved
  non-fuzzy entry compiles, an unapproved non-fuzzy entry falls back to
  English, and running without the option keeps today's behavior.
- [x] 4.4 Pass the ledger from the release and packaging path and report
  per-language coverage plus the English-fallback count; verify the report
  names a language with missing entries and does not use the catalog's own
  entry count as the denominator.
- [x] 4.5 Update the README translation commands for coverage, merge and
  approved compilation; verify each documented command runs from a clean
  checkout as written.

## 5. Cross-project translation memory

- [x] 5.1 Add `dev/tm_index.py` with the `sources` and `entries` schema, the
  mnemonic-stripped/NFKD/case-folded normalization, and a build from installed
  `.mo` catalogs; verify an idempotent rebuild produces the same counts.
- [x] 5.2 Implement dominance over distinct source projects and expose an
  exact/dominant lookup; verify one large catalog cannot outvote several
  agreeing projects.
- [x] 5.3 Add `po/tm-sources.json` and the licence gate: record project,
  language, licence and origin, and refuse a source with no licence or an
  incompatible one; verify GPL-2.0-only is excluded and BSD/GPL-3.0-or-later
  is indexed.
- [x] 5.4 Add `--import` for an upstream or Ubuntu language-pack tree and a
  `--stats` report; verify imported entries are attributed to their project
  and language.
- [x] 5.5 Document the corpus, the manifest and the licensing rule in the
  README; verify the documented build and stats commands run as written.

## 6. Model gate and qualification

- [x] 6.1 Add `po/translation-gate.json` separating releases (family, model
  id, revision) from deployments (provider, endpoint, quantization, prompt
  hash, decoding parameters, key environment variable); verify validation
  refuses duplicate proposer families, a judge that matches a proposer, and
  two deployments of one release used as independent voices.
- [x] 6.2 Implement per-release, per-language qualification from held-out
  reviewed entries, with the metric, tolerance and release recorded in the
  ledger; verify a passing release becomes eligible, a different release does
  not inherit, and a language with no baseline stays ineligible.
- [x] 6.3 Implement deployment conformance: an exact release identity plus an
  equivalent serving configuration plus a passing drift probe inherits the
  release's qualification; verify a second provider inherits without full
  qualification, a failed probe does not inherit, and a merely similar model
  requires full qualification.
- [x] 6.4 Add the fixed drift-probe set per language (30-50 stratified
  human-translated strings), record the release baseline at qualification,
  and run the probe before a batch; verify a score drop pauses approvals and
  queues the affected window for audit without demoting anything.
- [x] 6.5 Implement the capability report per language, listing qualified
  releases and deployments and naming languages with no machine path; verify
  a retired release keeps its approvals and is reported only as lost future
  capacity.
- [x] 6.6 Implement propose, blind judge and back-translation with abstention
  on any missing or failing evidence; verify a mocked run approves only when
  every check and the judge agree.
- [x] 6.7 Implement approve and revoke commands that clear the fuzzy flag only
  on approval and take effect at the next build; verify language-wide,
  deployment-wide and release-wide revocation each demote only their own
  approvals.
- [x] 6.8 Implement the random audit sample and the defect-rate demotion;
  verify a sample reports a rate without changing approvals, and a rate above
  the threshold demotes the language.
- [x] 6.9 Verify no model credential is read when the gate runs with an
  unset environment variable, and that the error names the missing variable
  without printing a secret.

## 7. Evidence ladder for high-impact strings

- [x] 7.1 Wire the evidence ladder into approval: unchanged pre-2026 text is
  `human-historical`, a mnemonic/placeholder-only change is
  `in-project-rebase`, and a dominant TM match plus the remaining evidence is
  `tm-consensus`; verify each class with a fixture.
- [x] 7.2 Enforce the high-impact rule: no evidence leaves the string English,
  and a strict `machine-strong` approval ships provisionally; verify a
  high-impact string cannot be approved from one weak proposal.
- [x] 7.3 Verify a TM match alone never approves a string, and that a
  `machine-strong` approval is reachable only when the strict evidence is
  present.
- [x] 7.4 Document the evidence ladder and the provisional-approval policy in
  the README and in the `translations` section of `AGENTS.md`; verify the
  documented classes match `translation_policy.py`.

## 8. Optional Rosetta import

- [x] 8.1 Add `dev/rosetta_import.py` to validate and merge a downloaded
  `.po` file or language-pack tree; verify it rejects a mismatched template
  and imports a valid export without network access.
- [x] 8.2 Document the one-off export flow, the read-only OAuth option and
  the absence of a bulk API in the README; verify the documented URLs and
  the `launchpadlib` example are correct and name no secret.
- [x] 8.3 Verify no CI workflow authenticates to Launchpad or reads a model
  credential; grep the workflows and run the checks with an empty
  environment.

## 9. Integration verification

- [x] 9.1 Run `pytest` and verify the coverage gate still passes with no new
  uncovered or partially covered lines.
- [x] 9.2 Run `ruff format --check .`, `ruff check .` and `ty check .`; verify
  all three report no diagnostics.
- [x] 9.3 Run `python3 dev/check_po.py`, `python3 dev/check_test_coverage.py`
  and the offline translation-tool tests; verify they pass without a network
  connection.
- [x] 9.4 Run `openspec validate --specs --strict --no-interactive` and
  verify it reports no failures.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Run `openspec validate --archived --no-interactive` and verify every task
  is ticked or rewritten as a prose bullet naming its tracking issue.
