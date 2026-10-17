## ADDED Requirements

### Requirement: The first selection can be drawn without an existing layer

The user SHALL be able to draw the selection rectangle in a layer pane on a
page that has no content in that pane's layer, without any prior OCR on the
page, and the rectangle SHALL become the current selection.

#### Scenario: First rectangle on a page that was never OCRed

- **WHEN** the user drags a rectangle in the Text layer pane of a page with
  no text layer
- **THEN** the rectangle SHALL become the current selection
- **AND** the same rectangle SHALL be shown as the selection on the Image tab

#### Scenario: First rectangle in the Annotation pane

- **WHEN** the user drags a rectangle in the Annotation pane of a page with
  no annotations
- **THEN** the rectangle SHALL become the current selection
- **AND** the same rectangle SHALL be shown as the selection on the Image tab

#### Scenario: First rectangle on a page whose layer is empty

- **WHEN** the page's text layer is empty because OCR found no text or
  because the layer was cleared
- **AND** the user drags a rectangle in the Text layer pane
- **THEN** the rectangle SHALL become the current selection
