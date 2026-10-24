# Layer Add Selection

## Purpose

Lets the user draw the selection rectangle for a new layer slice from the
layer pane itself, and keeps a single shared selection between the image view
and the layer panes.

## Requirements

### Requirement: The layer pane can draw a selection rectangle

The user SHALL be able to draw a selection rectangle directly in a layer pane
(Text layer or Annotation), and the resulting rectangle SHALL become the
current selection.

#### Scenario: Drawing a box in the Text layer pane

- **WHEN** the user drags a rectangle in the Text layer pane
- **THEN** the rectangle SHALL become the current selection
- **AND** the same rectangle SHALL be shown as the selection on the Image tab

#### Scenario: Drawing a box in the Annotation pane

- **WHEN** the user drags a rectangle in the Annotation pane
- **THEN** the rectangle SHALL become the current selection
- **AND** the same rectangle SHALL be shown as the selection on the Image tab

### Requirement: The image view and layer panes share one selection

The image view and the layer panes SHALL expose a single shared selection, so
that drawing in either pane replaces the selection in the other.

#### Scenario: Image selection replaces the layer selection

- **WHEN** the user draws a rectangle on the Image tab and then inspects the
  layer pane
- **THEN** the layer pane SHALL show the same rectangle as the selection

#### Scenario: Layer selection replaces the image selection

- **WHEN** the user draws a rectangle in a layer pane and then inspects the
  Image tab
- **THEN** the Image tab SHALL show the same rectangle as the selection

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

### Requirement: The image view paints the shared selection visibly

When the shared selection is set, the image view SHALL paint the selection
rectangle with the application's `.rubberband` style class, so the selection
is visible on the Image tab. The paint SHALL follow the GTK CSS cascade, so a
user-provided `.rubberband` rule in the user's gtk.css overrides the
application default.

#### Scenario: Shared selection is visible in the image view

- **WHEN** the user draws a selection in the image view or a layer pane so
  that the shared selection is set
- **AND** the application's stylesheets are installed
- **THEN** the Image tab SHALL paint a visible rectangle at the selection's
  widget coordinates using the application's `.rubberband` style

#### Scenario: User stylesheet recolours the image-view selection

- **WHEN** the user provides a `.rubberband` rule in their gtk.css with a
  background colour distinct from the application default
- **AND** a shared selection is set
- **THEN** the Image tab SHALL paint the selection with the user's colour
  instead of the application default
