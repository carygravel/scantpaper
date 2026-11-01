# image-view-tools Specification

## Purpose

Governs how the image view turns mouse-button presses and drags into
selection or panning actions, so users can select regions and move the
visible page with predictable controls.

## Requirements

### Requirement: Selector tool draws a selection with the primary button

When the selector tool is active, a primary-button press and drag SHALL
draw a rubber-band selection rectangle that follows the pointer, and SHALL
NOT pan the image.

#### Scenario: Primary drag draws a selection
- **WHEN** the user presses and drags with the primary button while the
  selector tool is active
- **THEN** a rubber-band selection rectangle SHALL follow the drag
- **AND** the image SHALL NOT pan

### Requirement: Dragger tool pans with the primary button

When the dragger tool is active, a primary-button press and drag SHALL pan
the image in the direction of the drag, and SHALL NOT draw a selection
rectangle.

#### Scenario: Primary drag pans the image
- **WHEN** the user presses and drags with the primary button while the
  dragger tool is active
- **THEN** the image SHALL pan in the direction of the drag
- **AND** no selection rectangle SHALL be drawn

### Requirement: Combined move/select tool pans with the middle button

The combined move/select tool SHALL be the default for the image view. It
SHALL draw a selection with the primary button and SHALL pan with a
middle-button press and drag, so panning is not lost to selection.

#### Scenario: Primary drag selects, not pans
- **WHEN** the combined tool is active and the user presses and drags
  with the primary button
- **THEN** a rubber-band selection rectangle SHALL follow the drag
- **AND** the image SHALL NOT pan

#### Scenario: Middle drag pans, not selects
- **WHEN** the combined tool is active and the user presses the middle
  button and drags
- **THEN** the image SHALL pan in the direction of the drag
- **AND** no selection rectangle SHALL be drawn

#### Scenario: A middle drag returns to selecting afterwards
- **WHEN** the user finishes a middle-button pan and then presses and
  drags with the primary button
- **THEN** a rubber-band selection rectangle SHALL follow the new drag
- **AND** the image SHALL NOT continue panning from the previous gesture

### Requirement: Middle-button presses are recognised by the tools

Only the combined move/select tool SHALL act on a middle-button press: it
SHALL begin a pan instead of ignoring the press. The selector tool and the
dragger tool SHALL ignore a middle-button press, neither panning nor
starting a selection. A secondary-button press SHALL NOT begin a selection
or a pan in any tool.

#### Scenario: Middle press is not ignored

- **WHEN** the user presses the middle button over the image while the
  combined tool is active
- **THEN** the view SHALL begin panning on drag
- **AND** no selection rectangle SHALL be drawn

#### Scenario: Selector ignores the middle button

- **WHEN** the user presses the middle button over the image while the
  selector tool is active
- **AND** the user moves the pointer while holding it
- **THEN** no selection rectangle SHALL be drawn
- **AND** the image SHALL NOT pan

#### Scenario: Dragger ignores the middle button

- **WHEN** the user presses the middle button over the image while the
  dragger tool is active
- **AND** the user moves the pointer while holding it
- **THEN** the image SHALL NOT pan
- **AND** no selection rectangle SHALL be drawn

#### Scenario: Secondary press is left to the context menu

- **WHEN** the user presses a secondary button over the image
- **THEN** no selection rectangle SHALL be drawn and the image SHALL NOT
  pan
