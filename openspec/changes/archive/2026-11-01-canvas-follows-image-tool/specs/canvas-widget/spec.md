# Spec Delta

## ADDED Requirements

### Requirement: Canvas mouse gestures follow the active viewer tool

The text-layer and annotation canvases SHALL route primary and middle
button presses according to the active viewer tool, so a tool has the
same meaning in a canvas as in the image view. The Pan tool SHALL start a
pan on a primary drag; the Select tool SHALL start a selection on a
primary press; the Select & Pan tool SHALL start a selection on a primary
press and a pan on a middle drag. The secondary button SHALL remain inert
in the canvases.

#### Scenario: Pan tool pans with the primary button

- **WHEN** the Pan tool is active
- **AND** the user presses and drags with the primary button in a canvas
- **THEN** the canvas view SHALL pan in the direction of the drag
- **AND** no selection rectangle SHALL be drawn
- **AND** no slice SHALL be focused

#### Scenario: Select tool selects with the primary button

- **WHEN** the Select tool is active
- **AND** the user presses and drags with the primary button in a canvas
- **THEN** a rubber-band selection rectangle SHALL follow the drag
- **AND** the canvas view SHALL NOT pan

#### Scenario: Select & Pan tool selects and pans

- **WHEN** the Select & Pan tool is active
- **AND** the user presses the middle button and drags in a canvas
- **THEN** the canvas view SHALL pan in the direction of the drag
- **AND** no selection rectangle SHALL be drawn

#### Scenario: Pan tool ignores the middle button

- **WHEN** the Pan tool is active
- **AND** the user presses the middle button and drags in a canvas
- **THEN** the canvas view SHALL NOT pan
- **AND** no selection rectangle SHALL be drawn

#### Scenario: Select tool ignores the middle button

- **WHEN** the Select tool is active
- **AND** the user presses the middle button and drags in a canvas
- **THEN** no selection rectangle SHALL be drawn
- **AND** the canvas view SHALL NOT pan

#### Scenario: A tool change applies to the next press

- **WHEN** a canvas is shown and the user changes the active viewer tool
- **THEN** the next primary-button press in that canvas SHALL follow the
  newly active tool

### Requirement: Canvas cursor reflects the active viewer tool

The Canvas SHALL show a grab cursor over the displayed page while the Pan
tool is active, and a grabbing cursor while a pan is in progress. While
the Select or Select & Pan tool is active, the Canvas SHALL show a
crosshair over the displayed page.

#### Scenario: Pan tool shows grab and grabbing cursors

- **WHEN** the Pan tool is active and the pointer is over the displayed
  page
- **THEN** the canvas SHALL show a grab cursor
- **AND** while a drag is panning, it SHALL show a grabbing cursor

#### Scenario: Selecting tools show a crosshair

- **WHEN** the Select or Select & Pan tool is active and the pointer is
  over the displayed page
- **THEN** the canvas SHALL show a crosshair cursor

## MODIFIED Requirements

### Requirement: Canvas supports middle-click drag panning

The Canvas SHALL allow the user to pan the view by middle-clicking and
dragging while the Select & Pan tool is active. While the Pan tool or the
Select tool is active, a middle-button press SHALL NOT pan the view and
SHALL NOT begin a selection.

#### Scenario: Middle-click drag

- **WHEN** the Select & Pan tool is active
- **AND** middle mouse button is pressed on the canvas
- **AND** the mouse is moved while holding
- **THEN** the view SHALL pan in the direction of mouse movement

### Requirement: Selection drawing depends on the page extent, not layer content

The canvas SHALL begin a selection drag whenever a selecting tool (Select
or Select & Pan) is active and the extent of the displayed page is known,
regardless of whether any layer content has been loaded, and SHALL NOT
begin one when no page extent is known or when the Pan tool is active.
While such a drag is in progress, the rubber-band rectangle SHALL be
drawn even though no layer content is displayed.

#### Scenario: Drag with a known page extent but no loaded layer

- **WHEN** a selecting tool is active
- **AND** the canvas knows the extent of the displayed page
- **AND** no text layer or annotations have been loaded into it
- **AND** the user presses and drags with the primary button
- **THEN** a rubber-band rectangle SHALL follow the pointer during the drag
- **AND** on release the rectangle SHALL become the current selection

#### Scenario: Drag with no known page extent

- **WHEN** a selecting tool is active
- **AND** no page extent is known (nothing has been displayed)
- **AND** the user presses and drags with the primary button
- **THEN** no selection drag SHALL start
- **AND** no rubber-band rectangle SHALL be drawn

#### Scenario: Pan tool drag does not start a selection

- **WHEN** the Pan tool is active
- **AND** the canvas knows the extent of the displayed page
- **AND** the user presses and drags with the primary button
- **THEN** the view SHALL pan
- **AND** no rubber-band rectangle SHALL be drawn

### Requirement: A primary press focuses only a word slice

While a selecting tool (Select or Select & Pan) is active, a
primary-button press on the Canvas SHALL focus a slice only when the
pointer lands on a word box. Any other press SHALL NOT focus anything,
SHALL NOT change the active navigation order or its current position, and
SHALL begin a selection drag when the page extent is known. While the Pan
tool is active, a primary press SHALL NOT focus anything and SHALL pan
instead. The geometric lookup that resolves a box at a point SHALL remain
available for choosing a new slice's parent.

#### Scenario: A press on a word focuses that word

- **WHEN** a selecting tool is active
- **AND** a word box is displayed under the pointer
- **AND** the user presses the primary button
- **THEN** that word SHALL become the focused slice
- **AND** no selection drag SHALL begin

#### Scenario: A press in the whitespace of a container starts a selection

- **WHEN** a selecting tool is active
- **AND** a line, paragraph, column or page box covers the pointer position
- **AND** no word box covers that position
- **AND** the page extent is known
- **AND** the user presses and drags the primary button
- **THEN** a rubber-band rectangle SHALL follow the pointer
- **AND** on release the rectangle SHALL become the current selection

#### Scenario: A press in container whitespace does not disturb navigation

- **WHEN** a selecting tool is active
- **AND** the editor is sorted by confidence and a word is focused
- **AND** the user presses the primary button in the whitespace of a
  container
- **THEN** no error SHALL be raised
- **AND** the focused slice SHALL remain the slice that was focused
- **AND** subsequent next and previous navigation SHALL continue from it

#### Scenario: Pan tool press does not focus

- **WHEN** the Pan tool is active
- **AND** a word box is displayed under the pointer
- **AND** the user presses the primary button
- **THEN** the view SHALL pan on drag
- **AND** no slice SHALL be focused

#### Scenario: Parent lookup still resolves a container

- **WHEN** a new slice is added at a selection whose centre lies in the
  whitespace of a container
- **THEN** the container SHALL be usable as the new slice's parent
- **AND** this SHALL NOT make the container a focusable slice
