# Proposal

## Why

The en_GB batch showed a pathological case. Two independent proposers returned
the same English text for 30 short labels, so the judge had no choice to make.
GLM spent about 339-412 output tokens per call deciding to answer `ABSTAIN`,
costing roughly $0.055 on 30 entries that produced no approvals. The judge was
also about 10x the cost of either proposer across the batch.

A judge cannot add information when every passing proposal is identical. The
gate should treat that agreement as the semantic verdict, skip the judge call,
and still keep the other evidence. The 30 en_GB strings have been filled
mechanically for this release, but the rule should prevent the same waste on
the next language.

## What Changes

- After the deterministic checks, detect whether every passing proposal has
  the same text and those proposals represent at least two independent
  families.
- When they do, approve the tie without calling the blind judge, record the
  tie in the approval evidence, and keep the existing provenance class.
- For a sentence, still require a back-translation that preserves meaning.
- When the passing proposals differ, keep the existing blind-judge path.
- Add tests that the judge is not called on a tie, that a sentence tie still
  back-translates, and that differing proposals still use the judge.
- Document the tie rule in `po/README.md`.

Out of scope: changing the judge model, adding a reasoning-effort setting,
and changing the provenance classes or the high-impact policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `machine-translation-gate`: update the semantic-evidence requirement so an
  identical proposal from two independent families is a valid verdict.

## Impact

- `dev/translation_gate.py`: the tie branch in `run_gate` and its evidence.
- `dev/tests/test_translation_gate.py`: tie, differing-proposal, sentence-tie
  and check-failure cases.
- `po/README.md`: tie-rule documentation.
- No new dependency and no shipped `scantpaper` change.
- No catalog or ledger change is required by the rule itself.
