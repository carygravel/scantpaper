# Tasks

## 1. Apply path

- [x] 1.1 Add `apply_decision()` to write `decision.translation` into
  `entry.msgstr`, clear fuzzy and record the approval; update
  `approve_decision()` to use it. Verify an empty entry is filled, a fuzzy
  proposal is replaced, and a decision without a translation is rejected
  without changing the catalog or ledger.

## 2. Batch command and selection

- [x] 2.1 Add the `translate` subparser with `--language`, `--catalog`,
  `--limit`, `--include-fuzzy`, `--max-cost`, `--tm`, `--dry-run` and
  `--json`; verify `python3 dev/translation_gate.py translate --help` lists
  every option.
- [x] 2.2 Select non-obsolete entries with empty translations by default,
  include non-empty fuzzy proposals only with `--include-fuzzy`, skip
  non-fuzzy entries, sort deterministically and apply `--limit`; verify tests
  for each selection rule.
- [x] 2.3 Run `run_gate` for each selected entry with its occurrences and the
  optional TM database, apply approved decisions, record gate runs, and leave
  abstentions fuzzy; verify one client call per proposer/judge/back-translation
  through a fake client and that an abstention is not written.
- [x] 2.4 Print a human summary and a JSON report with approved, abstained,
  skipped and unsupported entries, spend and remaining count; verify both
  forms with captured output.

## 3. Guards and budget

- [x] 3.1 Load and validate the role policy, then require every proposer and
  judge release to be qualified for the language and not paused; verify an
  unqualified release and a paused language exit non-zero without a model
  call, and a dry run reports the blockers without writing.
- [x] 3.2 Estimate the selected batch before the first call, refuse an
  over-budget high estimate, and stop before an entry whose high estimate
  would exceed the remaining budget; verify pre-flight and mid-run stops with
  no over-budget call and with remaining entries left fuzzy.

## 4. Unsupported entries and documentation

- [x] 4.1 Skip entries with `msgctxt` or `msgid_plural`, report each as
  unsupported, and leave them unchanged; verify a plural entry and a context
  entry are reported and a dry run writes nothing.
- [x] 4.2 Document the first targets (`en_GB`, `en_US` and `de`; there is no
  `en.po`), the merge/qualify/drift/translate sequence, `--limit`,
  `--include-fuzzy`, the total budget and the machine-strong policy for
  high-impact strings in `po/README.md`; verify the documented command matches
  the parser.

## 5. Integration verification

- [x] 5.1 Run `pytest`, `ruff format --check .`, `ruff check .`, `ty check .`,
  `python3 dev/check_test_coverage.py` and
  `openspec validate add-batch-translation-command --strict
  --no-interactive`; verify all pass and coverage does not regress.

## Workflow follow-up

- Archive the change after review.
- Consider separate changes for plural/context support and for making `gate`
  enforce qualification.
