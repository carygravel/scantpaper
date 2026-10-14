## ADDED Requirements

### Requirement: The initial sort selection is applied to navigation

When the text layer editor first appears, the sort method shown selected in
the control SHALL be the method used by navigation, so the displayed selection
and the actual navigation order agree from the start without any user action.

#### Scenario: First entry navigates by the displayed method

- **WHEN** the user enters the text layer editor for the first time with the
  sort control showing "Sort by confidence"
- **THEN** activating the "go to least confident text" control SHALL move to
  the least confident slice, as if the confidence sort had been selected
- **AND** the user SHALL NOT need to change and change back the sort selection
  to get confidence-based navigation

#### Scenario: The displayed selection always matches navigation

- **WHEN** the sort control is set to either method
- **THEN** the navigation order SHALL follow that method without the user
  having to toggle the selection
