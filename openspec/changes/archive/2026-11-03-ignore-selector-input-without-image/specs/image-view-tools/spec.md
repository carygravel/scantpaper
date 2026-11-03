# Spec Delta

## ADDED Requirements

### Requirement: Selection input is ignored while no image is displayed

When the image view displays no image, a primary press or drag SHALL NOT start
a selection, change the selection, pan the view, or raise an uncaught
exception. This SHALL apply to the Select tool and to the primary button of the
Select & Pan tool.

#### Scenario: Select tool ignores a press without an image

- **WHEN** the user presses the primary button and drags over the image view
  while no image is displayed and the Select tool is active
- **THEN** no selection rectangle SHALL be drawn
- **AND** the image SHALL NOT pan
- **AND** no exception SHALL be raised

#### Scenario: Select & Pan ignores a selection drag without an image

- **WHEN** the user presses the primary button and drags over the image view
  while no image is displayed and the Select & Pan tool is active
- **THEN** no selection rectangle SHALL be drawn
- **AND** the image SHALL NOT pan
- **AND** no exception SHALL be raised

#### Scenario: A press after an image appears still selects

- **WHEN** the user presses and drags over the image view after an image has
  been displayed
- **THEN** a selection rectangle SHALL follow the drag as usual

### Requirement: An ignored gesture leaves no partial selection state

After selection input was ignored because no image was displayed, a later
gesture SHALL start from its own press. The ignored gesture SHALL NOT leave a
drag origin, selection or active drag mode that changes the next selection.

#### Scenario: The next drag starts a fresh selection

- **WHEN** a primary press is ignored while no image is displayed
- **AND** an image is then displayed
- **AND** the user presses and drags with the primary button
- **THEN** the new selection SHALL start at the new press position
- **AND** it SHALL NOT continue from the ignored gesture's position
