# Spec Delta

## MODIFIED Requirements

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
