# Spec Delta

## MODIFIED Requirements

### Requirement: Every approval records a provenance class

The approval ledger SHALL record exactly one provenance class for each
approved string: `human-historical`, `human-review`, `in-project-rebase`,
`tm-consensus`, `machine-strong` or `machine-weak`. It SHALL also record the
language, context, msgid, msgstr, an evidence digest and compact evidence
summary, model release, deployment and approval date. The full evidence SHALL
be stored in a content-addressed evidence store.

#### Scenario: A machine approval records its class and evidence

- **WHEN** the gate approves a string as `machine-strong`
- **THEN** the approval contains the class, an evidence digest and summary,
  and the full proposals, judge verdict and check results are retrievable
  from the evidence store by that digest

#### Scenario: Evidence remains retrievable

- **WHEN** an audit resolves an approval's evidence digest
- **THEN** it reads the full evidence from the store, or reports the evidence
  as unavailable when the store is absent, without invalidating the approval

#### Scenario: An unknown class is rejected

- **WHEN** a ledger entry names a provenance class outside the six defined
  classes
- **THEN** validation rejects the entry rather than treating it as approved
