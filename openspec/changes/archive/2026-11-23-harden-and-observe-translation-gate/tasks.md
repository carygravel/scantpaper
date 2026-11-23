# Tasks

## 1. Back-translation failure becomes an abstention

- [x] 1.1 Make `back_translation_preserves` catch `ModelError`, return a tri-state (preserved / changed / unavailable), and not record the failed call; verify with a unit test that a raising client yields the unavailable state and no completion
- [x] 1.2 Map the unavailable state in `run_gate` to an abstention with reason `back-translation unavailable`, distinct from `back-translation changed the meaning`; verify with a test asserting the reason and `approved is False`
- [x] 1.3 Apply the same mapping in the `run_plural_gate` per-form back-translation loop, abstaining the whole plural entry when any form's judge call fails; verify with a plural test asserting the reason and that no form is applied
- [x] 1.4 Verify a failing back-translation judge no longer propagates out of `_run_batch`: a batch with one sentence whose back-translation client raises completes the remaining entries and reports the entry abstained (test)

## 2. Batch report distinguishes the new reason

- [x] 2.1 Count `back-translation unavailable` abstentions separately from judge-timeout and changed-meaning abstentions in `_run_batch` and `BatchReport`; verify with a test asserting the distinct count
- [x] 2.2 Render the new count in both the human line and the JSON form, mirroring the existing judge-timeout line; verify the human output names it and the JSON carries the field

## 3. Qualification reports live progress

- [x] 3.1 Add an action-scoped state path (`.cache/qualify/<release>.json`, language in the body) written atomically per item; verify two parallel releases for one language write distinct, non-clobbering files (test)
- [x] 3.2 Write selection, completed, matches-so-far, bare score against tolerance, spend, rate, estimate and in-flight call into the qualification state file; verify a mid-run state file reports done, matches and score (test)
- [x] 3.3 Wire `ObservedClient` around the qualification `client.complete` so `begin_call`/`end_call` populate the waiting field; verify a recorded waiting role appears in the state file (test)
- [x] 3.4 Keep the state file advisory: an unwritable or missing state file does not change the qualification result; verify with a test that a failing state write still returns the qualification record

## 4. Drift reports live progress

- [x] 4.1 Add an action-scoped state path (`.cache/drift/<deployment>.json`, language in the body) written atomically per probe item; verify two parallel deployments for one language never collide (test)
- [x] 4.2 Write selection, completed, matches-so-far, bare score against the drift threshold, spend, rate, estimate and in-flight call; verify a mid-run state file reports done, matches and score (test)
- [x] 4.3 Wrap the drift `client.complete` in `ObservedClient` for the waiting/stall signal; verify a recorded waiting role appears in the state file (test)
- [x] 4.4 Keep the drift state file advisory; verify a failing state write does not change the probe verdict (test)

## 5. `status` reports qualification and drift

- [x] 5.1 Enumerate the new state directories in `_status_languages` and build records with done/total, matches, bare score, tolerance-or-threshold, rate, ETA and age; verify `status --json` includes a live qualification record (test)
- [x] 5.2 Render qualification and drift records in the human line (done/total, matches, score, rate, ETA band, age) and reuse the abandoned/stalled logic; verify the human output and the stalled/abandoned cases (test)
- [x] 5.3 Verify `status` reports these records with no model credential and still exits zero (test)

## 6. Documentation and integration

- [x] 6.1 Document the `back-translation unavailable` reason and the widened `status` coverage in `po/README.md`; verify the documented commands/sections exist and stay within the 80-column wrap
- [x] 6.2 Add the user-visible line to `changelog.md` under `## 4.0.5 (unreleased)`; verify the file renders and wraps at 80 columns
- [x] 6.3 Run the full gate: `python3 dev/check_po.py`, `openspec validate --specs --strict --no-interactive`, `pytest`, `ruff check .`, `ruff format --check .`, `ty check .`; verify all pass with no new uncovered lines

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result with `openspec validate --archived --no-interactive`.
