# busy-action-handling Specification

## Purpose

Defines when a primary action requested while the application is still
preparing options is remembered and run, so a deliberate click is never
silently discarded.

## Requirements

### Requirement: Pending activation is remembered

While a primary action is temporarily unavailable because scan options are
being applied or reloaded, the application SHALL remember at most one
activation of that action and SHALL run it when the option work settles
successfully. The activation SHALL NOT be silently ignored.

#### Scenario: Scan clicked while a paper size is applied

- **WHEN** the user activates Scan while the paper-size or scan-option apply
  is still in progress
- **THEN** exactly one scan SHALL start when the apply completes
- **AND** the user SHALL NOT need a second activation

#### Scenario: Enter is equivalent to a click

- **WHEN** the user presses Enter on the scan dialog's default action while
  options are being applied
- **THEN** exactly one scan SHALL start when the apply completes

#### Scenario: Repeated activations coalesce

- **WHEN** the user activates Scan more than once during a single apply
- **THEN** at most one scan SHALL start when the apply completes

### Requirement: Primary actions stay activatable while options are prepared

A control that represents a primary action SHALL remain sensitive while the
application applies or reloads scan options, so both the press and the release
of a click are delivered. Busy state SHALL be shown by a progress indication
rather than by making the control insensitive.

#### Scenario: Scan is not ghosted during an option apply

- **WHEN** scan options are being applied or reloaded
- **THEN** the Scan control SHALL remain sensitive
- **AND** the dialog SHALL still show that it is busy

#### Scenario: Busy starts between press and release

- **WHEN** a pointer press on Scan is delivered and the option work starts
  before the release
- **THEN** the activation SHALL be remembered as pending
- **AND** the click SHALL NOT be discarded

### Requirement: Running work refuses a second action

While a scan is already running, the application SHALL refuse a second
activation of Scan instead of queueing it, so one action cannot start two
scans. The refusal SHALL be visible through the control's unavailable state.

#### Scenario: Second click during a scan does not queue a scan

- **WHEN** a scan is running and the user activates Scan again
- **THEN** no second scan SHALL be queued
- **AND** the Scan control SHALL communicate that the action is unavailable

### Requirement: Pending activations are one-shot and cleared

A pending activation SHALL run at most once and SHALL be cleared before the
action starts and when the dialog closes or the option work ends in error, so
it cannot replay during a later operation.

#### Scenario: Pending activation does not replay

- **WHEN** a pending Scan activation has started its scan
- **AND** a later option apply begins
- **THEN** that later apply SHALL NOT start another scan

#### Scenario: Closing the dialog clears the pending action

- **WHEN** the scan dialog is closed while an activation is pending
- **THEN** no scan SHALL start
- **AND** reopening the dialog SHALL start with no pending activation

#### Scenario: Option error does not silently swallow the activation

- **WHEN** the option apply ends in error while a Scan activation is pending
- **THEN** the error SHALL be reported to the user
- **AND** the pending activation SHALL be cleared rather than replayed later
