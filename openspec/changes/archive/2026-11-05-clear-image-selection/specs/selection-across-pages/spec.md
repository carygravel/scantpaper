# Spec Delta

## ADDED Requirements

### Requirement: The image selection can be cleared explicitly

The application SHALL provide a window action that clears the image selection
rectangle to no selection. The action SHALL be reachable from the View menu,
from a toolbar button next to the selection tools, and through the Escape key
while the main window has keyboard focus. A focused control that handles Escape
SHALL keep the key, so a widget with its own Escape behavior is not shadowed by
the shortcut.

#### Scenario: Clearing with the menu action

- **WHEN** an image selection rectangle is active and the user activates
  "Clear image selection" from the View menu
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

#### Scenario: Clearing with the toolbar button

- **WHEN** an image selection rectangle is active and the user activates the
  clear button next to the selection tools
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

#### Scenario: Clearing with Escape

- **WHEN** an image selection rectangle is active, the main window has focus,
  and the user presses Escape
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

### Requirement: Clearing the selection stops cross-page persistence

After the selection is cleared, navigating to another page SHALL NOT draw or
re-apply a rectangle. The cleared state SHALL behave like the initial state
before any selection was drawn.

#### Scenario: Cleared selection stays absent on page change

- **WHEN** the user clears the selection and then navigates to another page
- **THEN** no selection rectangle SHALL be drawn on the new page

#### Scenario: Clearing when no selection exists

- **WHEN** no image selection exists and the user activates the clear action
- **THEN** the application SHALL remain in a valid state
- **AND** no rectangle SHALL be drawn and no error SHALL be reported

### Requirement: Clearing releases selection-dependent controls

Clearing the selection SHALL disable the Add controls and SHALL leave Crop
with no region to apply. The cleared state SHALL NOT be represented as a
zero-size rectangle that still counts as a selection.

#### Scenario: Add is disabled after clearing

- **WHEN** a selection is active and the user clears it
- **THEN** the Add control SHALL be insensitive

#### Scenario: Crop is not attempted after clearing

- **WHEN** the user clears the selection and then activates Crop
- **THEN** no crop SHALL be applied
- **AND** no invalid-selection error SHALL be reported

#### Scenario: Crop dialog drops the cleared rectangle

- **WHEN** the user clears the selection while the Crop dialog is open
- **THEN** the dialog SHALL no longer consider the rectangle active
- **AND** the clear action SHALL NOT raise an error

### Requirement: Clear action availability follows the selection

The clear action, its menu item, and its toolbar button SHALL be insensitive
while no image selection exists and sensitive while one does.

#### Scenario: Clear is insensitive without a selection

- **WHEN** no image selection exists
- **THEN** the "Clear image selection" menu item and toolbar button SHALL be
  insensitive

#### Scenario: Clear is sensitive with a selection

- **WHEN** an image selection rectangle is active
- **THEN** the "Clear image selection" menu item and toolbar button SHALL be
  sensitive
