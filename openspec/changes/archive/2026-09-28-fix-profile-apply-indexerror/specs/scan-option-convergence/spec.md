## ADDED Requirements

### Requirement: Profile application never crashes on completion

Applying a scan-option profile SHALL complete without raising an exception
when finalization re-enters the `changed-current-scan-options` handler, even
when the profile-apply stack is already empty. A completed profile apply SHALL
always leave the profile name committed and the scan dialog responsive (not in
a "wait" cursor state).

#### Scenario: Finalize re-enters the handler with an empty apply stack

- **WHEN** applying a profile whose last backend option finishes, so
  completion re-enters the changed-current-scan-options handler after the
  profile-apply stack has already been cleared
- **THEN** no `IndexError` (or any exception) is raised
- **AND** the dialog cursor is restored to the default
- **AND** the applied profile name is committed and shown as active

#### Scenario: Applying any multi-option profile terminates cleanly

- **WHEN** a profile containing several backend options (for example mode,
  resolution, and source) is applied to a Brother-style scanner
- **THEN** the apply terminates without a traceback
- **AND** the dialog remains open and responsive
