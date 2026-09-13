## Purpose

Guarantees that applying scan options from a profile terminates even when a
scanner backend couples or aliases options so that setting one reverts
another, by detecting per-option reversion, dropping the unruly option, and
capping total reload work.

## ADDED Requirements

### Requirement: Continuous reloading terminates with a settled dialog
Applying a scan-option profile SHALL always terminate. When the backend keeps
reverting an option every time it is re-applied, the apply SHALL not loop
indefinitely and SHALL leave the scan dialog usable without showing the
"Reload recursion limit exceeded" error dialog.

#### Scenario: Coupled options do not hang the dialog
- **WHEN** a profile contains options that the backend couples (for example
  a media-size option and its alias, or a media size and numeric geometry)
- **THEN** the apply terminates within a small bounded number of reload
  rounds
- **AND** the scan dialog remains open and responsive
- **AND** no "Reload recursion limit exceeded" error is shown

#### Scenario: Backend reverts an option after every set
- **WHEN** the backend reverts a set option's value on each reload
- **THEN** the apply gives up on that option after a small number of failed
  re-applies
- **AND** the remaining options are still applied

### Requirement: Give up on a specific reverted option
When an option has been re-applied a small fixed number of times (K=2) because
the backend reverted it after a reload, the application SHALL stop re-applying
that option for the rest of the apply and SHALL remove it from the current
scan options so it is not re-applied by later reloads or persisted in saved
defaults. The remaining options SHALL continue to be applied in profile order
("last writer wins").

#### Scenario: Reverted media-size alias is dropped and the rest are set
- **WHEN** setting option A reverts option B, and re-setting B reverts A
  again
- **THEN** the option last reverted (K re-applies) is dropped from the
  current scan options
- **AND** the apply completes after the drop without further reloads

#### Scenario: Dropped option is not persisted in saved defaults
- **WHEN** an option was dropped because the backend kept reverting it
- **THEN** the option is not written back to the saved default scan options
  when the configuration is saved

### Requirement: Culprit is identified in the log
Whenever the application gives up on an option because it kept being reverted,
the application SHALL write a log entry naming the option and the reason for
giving up.

#### Scenario: Log entry names the dropped option
- **WHEN** an option is dropped due to repeated reversion
- **THEN** a log entry is written that contains the option name and states
  that the option was reverted and dropped

### Requirement: Total reload-work backstop
In addition to per-option give-up, the application SHALL cap the total number
of reloads across all options with a bound that is linear in the number of
scan options, so that a pathological backend cannot drive unbounded reload
work.

#### Scenario: Hostile backend triggers the total cap
- **WHEN** a backend reverts options so persistently that the total reload
  count across an apply exceeds the linear bound based on the current option
  count
- **THEN** the apply aborts with an informative error logged
- **AND** no infinite reload loop runs

### Requirement: Counters reset at the start of each apply
Reload and reversion counters SHALL be reset at the start of every top-level
profile application, so that unrelated apply attempts do not accumulate toward
the same budget and a later, healthy apply is not harmed by an earlier,
pathological one.

#### Scenario: Healthy apply after a pathological one is unaffected
- **WHEN** a profile apply previously gave up on a reverted option, and then a
  different profile is applied
- **THEN** the second apply starts with fresh counters
- **AND** options that were healthy in the second apply are set normally
  without being dropped

### Requirement: No infinite recursion on option-count tripping
When a top-level profile apply is re-entered by its own reloads (for example
while setting a paper size or a stored default profile), the counters SHALL
be owned by the top-level apply so that re-entry does not double-count or
leak state.

#### Scenario: Recursive apply re-entry shares the top-level budget
- **WHEN** a reload triggers a nested application of the same profile within
  one top-level apply
- **THEN** the nested application shares the top-level apply's counters
- **AND** the combined work is capped by the same linear bound