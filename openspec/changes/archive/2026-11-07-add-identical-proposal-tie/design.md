# Design

## Context

See `proposal.md` - Why.

`run_gate()` proposes from every configured proposer, checks that at least two
families are represented, runs deterministic checks, then calls `blind_judge`
on the passing proposals. The en_GB batch produced 30 cases where both
proposers returned exactly the same text; the judge answered `ABSTAIN` after a
long reasoning pass, and the gate abstained. The judge cannot add information
when there is only one distinct passing text.

## Goals / Non-Goals

**Goals:**

- Skip the judge when every passing proposal is identical and independent
  families produced them.
- Record the tie explicitly and keep the existing approval evidence.
- Keep back-translation and deterministic checks unchanged.
- Remove the 30-entry class of wasted judge calls and abstentions.

**Non-Goals:**

- Changing the judge model or its reasoning effort.
- Changing the provenance classes or the high-impact policy.
- Bypassing the two-family independence rule.

## Decisions

### Detect the tie after the deterministic checks

The tie is computed from the `passing` proposals, after:

- at least two independent families have proposed;
- every passing proposal has passed the deterministic checks.

The rule is:

```python
texts = {proposal.text.strip() for proposal in passing}
families = {proposal.family for proposal in passing}
tie = len(texts) == 1 and len(families) >= 2
```

Exact text after trimming is used, not the normalized comparison used by the
deterministic checks. Case, mnemonic underscores and punctuation are part of
a UI translation; if two families disagree on any of them, the judge still
has a real choice.

### Skip the judge only for a tie

When `tie` is true, the gate selects the first passing proposal as the
preferred one, sets the verdict to `identical`, and does not call
`blind_judge`. The evidence records:

```json
"judge": {
  "tie": true,
  "verdict": "identical",
  "families": ["deepseek-flash", "minimax"]
}
```

When the proposals differ, the existing judge path and its
`{"deployment": ..., "verdict": ...}` evidence are unchanged. A single
passing proposal is not a tie and still uses the judge.

### Keep the other evidence

A tie replaces only the judge's choice. It does not replace:

- the two-family independence requirement;
- the deterministic checks;
- a back-translation for a sentence;
- the high-impact evidence policy.

If a sentence's back-translation fails, the tie still abstains. If a proposal
fails a deterministic check, it is not part of `passing`, so a tie is not
possible with a failing proposal.

### Provenance and reporting

The approval keeps the existing `machine-strong` class, or `tm-consensus`
when a dominant translation-memory match agrees. The tie is evidence detail,
not a new provenance class. `record_gate_run()` continues to use the winning
deployment's record; the call list simply has no judge call for a tie.

## Risks / Trade-offs

- **Two families can agree on a bad translation** -> the tie removes a third
  opinion. The deterministic checks, the sentence back-translation, the
  high-impact policy, the audit sample and revocation remain the safety net.
  The judge had no choice to make in these cases, so it was not providing a
  third opinion anyway.
- **Exact-text tie is conservative** -> a case or whitespace difference still
  goes to the judge, which may cost more but preserves a real decision.
- **Evidence shape changes for ties** -> any consumer that assumes a judge
  deployment must handle the `tie` form. The cost report reads calls, not the
  judge evidence; tests cover the approval record.
- **Batch cost** -> the tie rule removes the 30 judge calls that returned
  `ABSTAIN`; it does not reduce the cost of genuine disagreements.

## Migration Plan

No migration. The rule is additive and the catalog/ledger formats do not
change. Existing approvals remain valid. Rollback is removing the tie branch;
the judge path is unchanged.

## Open Questions

None.
