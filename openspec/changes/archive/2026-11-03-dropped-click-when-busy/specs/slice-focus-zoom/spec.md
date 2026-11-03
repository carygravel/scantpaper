# Spec Delta

## ADDED Requirements

### Requirement: The focus-level control opens on first activation

The focus-level control SHALL open its popover on every activation and SHALL
NOT retain an active popover while its control bar is hidden. Hiding the bar
for the inactive layer or the Image page SHALL close the popover before the
bar is hidden.

#### Scenario: First activation after the bar is shown

- **WHEN** a layer control bar that was hidden is shown again
- **AND** the user activates its focus-level control
- **THEN** the popover SHALL open on that first activation

#### Scenario: Switching away closes the popover

- **WHEN** the focus-level popover is open
- **AND** the user switches to a layer or page that hides the control bar
- **THEN** the popover SHALL close

#### Scenario: Returning does not require two clicks

- **WHEN** the popover was closed by hiding its control bar
- **AND** the bar is shown again
- **AND** the user activates the control once
- **THEN** the popover SHALL open
- **AND** the user SHALL NOT need a second activation

#### Scenario: Each layer's control is independent

- **WHEN** the text-layer popover is open
- **AND** the user switches to the annotation layer and activates its
  focus-level control
- **THEN** the text-layer popover SHALL be closed
- **AND** the annotation-layer popover SHALL open on that first activation
