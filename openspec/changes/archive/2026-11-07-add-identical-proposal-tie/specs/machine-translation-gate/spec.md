# Spec Delta

## MODIFIED Requirements

### Requirement: Approval requires deterministic and semantic evidence

The gate SHALL approve a string only when every deterministic check passes
for the source and the translation and the semantic evidence agrees. Semantic
evidence SHALL include either a blind judge verdict or, when every passing
proposal has the same text and at least two independent families proposed it,
the agreement of those families. For a sentence, a back-translation that
preserves meaning SHALL still be required. A failing or missing piece of
evidence SHALL block approval.

#### Scenario: All evidence agrees

- **WHEN** both proposals pass the deterministic checks, the judge prefers one
  of them, and any back-translation preserves meaning
- **THEN** the string is approved and every piece of evidence is recorded

#### Scenario: Identical proposals are a tie

- **WHEN** every passing proposal has the same text, at least two independent
  families proposed it, and every deterministic check passes
- **THEN** the gate approves without a judge call, records the tie as the
  semantic verdict, and still back-translates a sentence

#### Scenario: Differing proposals are judged

- **WHEN** the passing proposals do not all have the same text
- **THEN** the gate calls the blind judge before approving

#### Scenario: A placeholder check fails

- **WHEN** the preferred proposal fails a placeholder, plural, markup or
  render check even though the judge prefers it or the proposals tie
- **THEN** the string is not approved

#### Scenario: Back-translation changes meaning

- **WHEN** a sentence proposal back-translates to a meaning that differs from
  the source
- **THEN** the string is not approved
