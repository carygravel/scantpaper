# Layer Editing

## MODIFIED Requirements

### Requirement: Slices can be added and duplicated

Adding a slice SHALL insert a new slice at the current selection, and
duplicating SHALL insert a copy of the current text at the current selection.
Both SHALL be written to the page's layer and drawn on the page. Adding
SHALL be possible when the selection was drawn in the layer pane as well as
on the image view.

#### Scenario: Adding a slice at the selection

- **WHEN** the user drags a selection, types a text and activates the add
control
- **THEN** a slice with that text SHALL exist at the selected rectangle
- **AND** it SHALL be drawn on the page
- **AND** the new slice SHALL be focused for further editing

#### Scenario: Adding a slice from a layer-pane selection

- **WHEN** the user draws a rectangle in the Text layer pane, types a text
  and activates the add control
- **THEN** a slice with that text SHALL exist at the drawn rectangle
- **AND** it SHALL be drawn on the page

#### Scenario: Adding uses a placeholder when no text is given

- **WHEN** the user activates the add control with an empty control and a
  selection
- **THEN** a slice SHALL be added at the selection with placeholder text

#### Scenario: Duplicating a slice

- **WHEN** the user activates the duplicate control
- **THEN** a second slice with the same text SHALL exist at the current
selection
- **AND** the original slice SHALL remain unchanged

## ADDED Requirements

### Requirement: The Add control is disabled without a selection

The Add control SHALL be disabled (ghosted) whenever there is no current
selection, and SHALL be enabled whenever there is one. This applies to both
the text and annotation editors.

#### Scenario: No selection disables the Add control

- **WHEN** there is no selection rectangle
- **THEN** the Add control SHALL be disabled
- **AND** activating it SHALL have no effect

#### Scenario: A selection enables the Add control

- **WHEN** a selection rectangle exists, whether drawn in the image view or a
  layer pane
- **THEN** the Add control SHALL be enabled

### Requirement: The disabled Add control explains itself

While the Add control is disabled it SHALL show a tooltip stating that a
rectangle must be drawn or selected before adding, so the reason for the
disabled state is discoverable.

#### Scenario: Tooltip on the disabled Add control

- **WHEN** the Add control is disabled
- **THEN** hovering it SHALL show a tooltip that a rectangle must be drawn or
  selected first
