## ADDED Requirements

### Requirement: Selection drawing depends on the page extent, not on layer content

The canvas SHALL begin a selection drag whenever the extent of the displayed
page is known, regardless of whether any layer content has been loaded, and
SHALL NOT begin one when no page extent is known. While such a drag is in
progress, the rubber-band rectangle SHALL be drawn even though no layer
content is displayed.

#### Scenario: Drag with a known page extent but no loaded layer

- **WHEN** the canvas knows the extent of the displayed page
- **AND** no text layer or annotations have been loaded into it
- **AND** the user presses and drags with the primary button
- **THEN** a rubber-band rectangle SHALL follow the pointer during the drag
- **AND** on release the rectangle SHALL become the current selection

#### Scenario: Drag with no known page extent

- **WHEN** no page extent is known (nothing has been displayed)
- **AND** the user presses and drags with the primary button
- **THEN** no selection drag SHALL start
- **AND** no rubber-band rectangle SHALL be drawn
