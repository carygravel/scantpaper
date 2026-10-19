## ADDED Requirements

### Requirement: Split view shows the active layer's canvas

In a split view mode the pane beside the image SHALL show the active layer's
canvas, so the layer selected for editing is also the layer on screen. Only one
layer canvas SHALL be shown beside the image at a time.

#### Scenario: The text canvas is shown for the text layer

- **WHEN** the active layer is the text layer in a split view mode
- **THEN** the text layer canvas SHALL be shown beside the image
- **AND** the annotation canvas SHALL NOT be shown

#### Scenario: The annotation canvas is shown for the annotation layer

- **WHEN** the active layer is the annotation layer in a split view mode
- **THEN** the annotation layer canvas SHALL be shown beside the image
- **AND** the text layer canvas SHALL NOT be shown

#### Scenario: Changing the active layer swaps the canvas

- **WHEN** the user switches the active layer while in a split view mode
- **THEN** the pane beside the image SHALL swap to the newly active layer's
  canvas
- **AND** the previously shown layer canvas SHALL be removed from the pane

#### Scenario: Switching out of tabbed mode detaches the active canvas

- **WHEN** the user switches from tabbed mode to a split view mode
- **THEN** the active layer's canvas SHALL be moved out of the notebook into the
  split pane
- **AND** it SHALL remain the canvas shown beside the image

### Requirement: The edit bar takes only its minimum height

The control bar below the view SHALL be given only the height it needs, so the
image or split view above it keeps the remaining vertical space. This SHALL hold
on first paint, without the user having to drag the divider.

#### Scenario: The bar does not claim half the view at startup

- **WHEN** the window is first shown with a layer active
- **THEN** the edit bar SHALL occupy only its minimum height
- **AND** the view above it SHALL keep the rest of the available height
