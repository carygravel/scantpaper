# Canvas Widget

## Purpose

Provide a Cairo-based rendering widget for displaying and interacting with OCR bounding boxes and text overlaid on scanned document images.

## Requirements

### Requirement: Canvas renders OCR bounding boxes and text

The Canvas widget SHALL render a scene graph of OCR elements (page, carea, paragraph, line, word) as colored bounding rectangles with rotated text. When the text of an element in the scene graph changes, the Canvas SHALL redraw that element with its new text on the next frame.
When drawing text over the scanned image, the Canvas SHALL align the rendered text by its baseline to the baseline position derived from the hOCR `baseline` attribute (respecting rotation and slope) rather than vertically centering the rendered text's ink box in the bounding box.

#### Scenario: Single word displayed
- **WHEN** `set_text()` is called with a single word bbox at (10, 20, 100, 40) with text "hello" and hOCR baseline information
- **THEN** the canvas SHALL display a rectangle from (10, 20) to (100, 40) and the text "hello" positioned so its baseline aligns with the baseline derived from the hOCR data

#### Scenario: Confidence-colored bounding box
- **WHEN** a word has confidence 95
- **AND** max_color is "black" and min_color is "red"
- **AND** max_confidence is 95 and min_confidence is 50
- **THEN** the rectangle and text SHALL be drawn in black (the confidence equals max_color threshold)

#### Scenario: Low confidence coloring
- **WHEN** a word has confidence 25
- **AND** max_color is "black" and min_color is "red"
- **AND** max_confidence is 95 and min_confidence is 50
- **THEN** the rectangle and text SHALL be drawn in red (the confidence is below min_confidence threshold)

#### Scenario: Text inside bounding box is rotated
- **WHEN** a word has textangle 90
- **THEN** the rendered text SHALL be rotated 90 degrees within its bounding box and positioned according to its baseline

#### Scenario: Multiple words on same line
- **WHEN** `set_text()` is called with two words on the same line (depth 3) with different x positions
- **THEN** both words SHALL be displayed at their respective positions with correct bounding boxes

#### Scenario: Changed text is redrawn
- **WHEN** a word's text is changed after it has already been drawn at least once
- **THEN** the next drawn frame SHALL show the new text for that word
- **AND** SHALL NOT show the text the word had before the change

#### Scenario: Baseline alignment for words with descenders
- **WHEN** rendering a word that contains descender characters (e.g., "jumps", "quick", "happy") using its hOCR baseline
- **THEN** the rendered text SHALL be vertically positioned using baseline alignment so that descenders extend below the baseline in a manner consistent with the hOCR's baseline coordinate system

#### Scenario: Baseline alignment for words without descenders
- **WHEN** rendering a word with no descender characters (e.g., "man", "run", "sun") using its hOCR baseline
- **THEN** the rendered text SHALL be vertically positioned using baseline alignment to match the baseline position from hOCR, avoiding the vertical shift that occurs with pure vertical centering of the ink box

### Requirement: Canvas fits slice text along the correct axis

The Canvas SHALL choose the axis that rendered slice text spans from the
slice's drawn angle: a slice drawn at 0 or 180 degrees SHALL scale its text to
span the slice's width, and a slice drawn at 90 or 270 degrees SHALL scale its
text to span the slice's height. This SHALL hold whether the drawn angle comes
from the slice's own text angle or from an ancestor's accumulated angle.

#### Scenario: A 180-degree slice is sized like an upright slice

- **WHEN** two slices carry the same text and the same bounding-box width and
  height, one drawn at 0 degrees and the other at 180 degrees
- **THEN** the text of the 180-degree slice SHALL be drawn at the same size as
  the text of the upright slice
- **AND** it SHALL NOT be shrunk to the slice's height

#### Scenario: A 90-degree slice spans its height

- **WHEN** a slice is drawn at 90 degrees in a bounding box taller than it is
  wide
- **THEN** its text SHALL be drawn spanning the slice's height

#### Scenario: An inherited 180-degree angle selects the width

- **WHEN** a slice with no text angle of its own is drawn at 180 degrees because
  of an ancestor's accumulated angle
- **THEN** its text SHALL be drawn spanning the slice's width

### Requirement: Canvas supports zoom

The Canvas SHALL support zoom levels between 0.001 and 15.0, with all rendered content scaling proportionally.

#### Scenario: Zoom set to 2.0
- **WHEN** `zoom` is set to 2.0
- **THEN** all rendered content SHALL appear at 2x size

#### Scenario: Zoom bound at maximum
- **WHEN** `zoom` is set to 20.0
- **THEN** `zoom` SHALL be clamped to 15.0
- **AND** the "zoom-changed" signal SHALL be emitted with value 15.0

#### Scenario: Zoom bound at minimum
- **WHEN** `zoom` is set to 0.0
- **THEN** `zoom` SHALL be clamped to 0.001
- **AND** the "zoom-changed" signal SHALL be emitted with value 0.001

#### Scenario: zoom-changed signal emitted
- **WHEN** `zoom` property changes to a new value
- **THEN** the "zoom-changed" signal SHALL be emitted with the new value as a float

### Requirement: Canvas supports offset (pan)

The Canvas SHALL support an offset property that controls which portion of
the scene is visible, clamped to prevent viewing outside the image bounds.
The offset SHALL use the same sign convention as ImageView: a positive
offset shifts the image rightward in widget space. Clamping SHALL happen
against the canvas's live allocation: an offset pushed while the canvas has
no usable allocation (unmapped or zero-sized) SHALL be stored unclamped and
SHALL be clamped at the canvas's next allocation, never discarded.

#### Scenario: Offset set within bounds
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset` is set to (100, 200)
- **THEN** the canvas SHALL scroll so that the image pixel (100, 200) aligns
  with the widget origin

#### Scenario: Offset clamped to prevent edge visibility
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset.x` is set to -50
- **THEN** `offset.x` SHALL be clamped to 0

#### Scenario: offset-changed signal
- **WHEN** `offset` changes to a new value
- **THEN** the "offset-changed" signal SHALL be emitted with (x, y) integers

#### Scenario: Offset matches ImageView convention
- **WHEN** offset is set on the ImageView
- **THEN** the same offset value SHALL produce the same image-visible-region
  on both widgets

#### Scenario: Offset pushed while unallocated is clamped at allocation

- **WHEN** the canvas has a known page extent and is unmapped (zero
  allocation)
- **AND** `offset` is set to (357, 0)
- **AND** the canvas is then allocated
- **THEN** the stored offset SHALL be clamped against the new allocation at
  that allocation
- **AND** the offset SHALL NOT have been clamped to (0, 0) by the earlier
  push

### Requirement: Canvas zoom uses uniform scaling

The Canvas SHALL apply zoom as a uniform scale factor, without centering about the widget center. Centering of small images SHALL be handled by the offset clamping mechanism, matching ImageView behavior.

#### Scenario: Zoom does not re-center widget
- **WHEN** `zoom` is set to 2.0 at offset (0, 0)
- **THEN** image pixel (0, 0) SHALL appear at widget coordinate (0, 0)
- **AND** image pixel (100, 100) SHALL appear at widget coordinate (200, 200)

### Requirement: Canvas supports clear_text

The Canvas SHALL clear all displayed text and reset internal state.

#### Scenario: Clear after set_text
- **WHEN** `set_text()` has been called with words
- **AND** `clear_text()` is called
- **THEN** no text or bounding boxes SHALL be displayed
- **AND** `get_pixbuf_size()` SHALL return None
- **AND** the color lookup table SHALL be invalidated

### Requirement: Canvas supports hit testing

The Canvas SHALL identify which Bbox contains a given coordinate point.

#### Scenario: Click inside a word bbox
- **WHEN** a word bbox exists at (10, 20, 100, 40)
- **AND** the point (50, 30) is tested
- **THEN** `get_bbox_at()` SHALL return that Bbox

#### Scenario: Click outside any bbox
- **WHEN** no bbox exists at the given coordinates
- **AND** point (0, 0) is tested
- **THEN** `get_bbox_at()` SHALL raise ReferenceError

### Requirement: Canvas supports add_box for editing

The Canvas SHALL support adding new words (bounding boxes with text) to the scene graph at runtime, supporting the text editing workflow.

#### Scenario: Add word to existing parent
- **WHEN** a page bbox exists as root
- **AND** a new word bbox is added with `add_box(parent=page, bbox=..., text="new")`
- **THEN** the new word SHALL appear in the display
- **AND** the word SHALL be added to the confidence index

#### Scenario: Add word without parent (auto-lookup)
- **WHEN** `add_box()` is called without a parent argument
- **AND** a bbox at the given coordinates exists
- **THEN** the new word SHALL be added as a child of the bbox at those coordinates

### Requirement: Canvas supports update_box for text editing

The Canvas SHALL support updating an existing word's text, bounding box, and confidence after user edits. The word's position within its parent's children SHALL reflect the new bounding box, so that serialising the scene graph yields the words in reading order.

#### Scenario: Update word text and bounding box
- **WHEN** a word bbox exists with text "old" at (10, 20, 100, 40)
- **AND** `update_box()` is called with text "new" and a new selection rectangle (15, 25, 95, 35)
- **THEN** the displayed text SHALL be "new"
- **AND** the bounding box SHALL be (15, 25, 95, 35)
- **AND** the confidence SHALL be set to 100
- **AND** the "text-changed" signal SHALL be emitted on the Bbox

#### Scenario: Moving a word reorders it among its siblings
- **WHEN** a word on a line is updated with a selection rectangle to the right
  of a word that currently follows it
- **THEN** the word SHALL become a later child of its parent
- **AND** `hocr()` SHALL serialise the words in their new order

#### Scenario: Delete box when text is empty

`update_box()` is a data setter, so an empty text does not remove the bbox;
removal is an explicit Canvas operation that the layer editor calls instead, so
that an emptied slice can be routed through it (see the layer-editing delta for
the user-visible behaviour).

- **WHEN** `update_box()` is called with text ""
- **THEN** the bbox SHALL remain in the scene graph
- **AND** `hocr()` SHALL still contain the bbox, with empty text
- **AND** the bbox SHALL remain in the confidence index
- **AND** the bbox SHALL remain reachable by position-based navigation

### Requirement: Canvas supports delete_box

The Canvas SHALL support removing a word from the scene graph. A removed word
SHALL no longer be drawn, SHALL no longer be reachable by either navigation
order, and SHALL not appear in `hocr()` output.

#### Scenario: Delete existing bbox
- **WHEN** a word exists
- **AND** `delete_box()` is called on it
- **THEN** the word SHALL be removed from the scene graph
- **AND** the word SHALL no longer be drawn
- **AND** the word SHALL be absent from `hocr()` output
- **AND** the word SHALL be removed from the confidence index
- **AND** the position index SHALL advance to the next word (or previous if no
next)

#### Scenario: Deleted word is unreachable in either sort order
- **WHEN** a word is deleted
- **THEN** navigating forward through the confidence order SHALL skip it
- **AND** navigating forward through the position order SHALL skip it

#### Scenario: Deleting the last remaining word
- **WHEN** the only word on a page is deleted
- **THEN** it SHALL be absent from `hocr()` output
- **AND** `hocr()` SHALL NOT contain an element with an empty text
- **AND** navigation SHALL report that there is no current word

### Requirement: Canvas keeps navigation indices consistent with the scene graph

The Canvas SHALL maintain its confidence-sorted index and its position-based
iterator so that both reflect the current contents of the scene graph after any
addition, correction, or deletion. Neither index SHALL retain a reference to a
word that is no longer in the scene graph, and neither SHALL be left pointing at
a word that has been removed.

#### Scenario: Position order stays correct after a deletion
- **WHEN** words are deleted while the position order is the active order
- **THEN** iterating forwards in position order SHALL visit exactly the
  remaining words, in reading order
- **AND** SHALL NOT visit any deleted word

#### Scenario: Confidence order stays correct after a deletion
- **WHEN** words are deleted while the confidence order is the active order
- **THEN** iterating forwards in confidence order SHALL visit exactly the
  remaining words
- **AND** the current word SHALL remain defined after each deletion

#### Scenario: Correcting a word moves it in confidence order
- **WHEN** a low-confidence word is corrected and its confidence becomes 100
- **THEN** confidence order SHALL place it at the high-confidence end
- **AND** the confidence index SHALL no longer list it at its old position

### Requirement: Canvas removes emptied ancestor boxes from the scene graph

When a word is deleted, the Canvas SHALL remove any ancestor that has no words
left beneath it, so that the serialised scene graph does not contain empty
lines, paragraphs, columns or pages.

#### Scenario: Emptied line is removed
- **WHEN** the only word of a line is deleted
- **THEN** the line SHALL no longer be a child of its parent
- **AND** `hocr()` SHALL NOT contain an element for that line

#### Scenario: Emptied paragraph is removed
- **WHEN** the only line of a paragraph is deleted
- **THEN** the paragraph SHALL no longer be a child of its parent
- **AND** `hocr()` SHALL NOT contain an element for that paragraph

#### Scenario: The page box itself is retained
- **WHEN** every word on the page is deleted
- **THEN** `hocr()` SHALL NOT contain any word
- **AND** the serialised output SHALL NOT contain an empty word, line, paragraph
  or column element

### Requirement: Canvas produces hOCR output

The Canvas SHALL export the current scene graph as hOCR (HTML + XHTML) format.

#### Scenario: Export single word
- **WHEN** a word "hello" exists at bbox (10, 20, 100, 40) with confidence 95
- **THEN** `hocr()` SHALL return a valid hOCR string containing `<span class='ocr_word' title='bbox 10 20 100 40; x_wconf 95'>hello</span>`

#### Scenario: Export empty canvas
- **WHEN** `clear_text()` has been called
- **AND** no words are displayed
- **THEN** `hocr()` SHALL return ""

### Requirement: Canvas supports text sorting modes

The Canvas SHALL support iterating through words by confidence or by reading position.

#### Scenario: Sort by confidence
- **WHEN** words with different confidence levels exist
- **AND** `sort_by_confidence()` is called
- **THEN** `get_first_bbox()` SHALL return the highest-confidence word
- **AND** `get_next_bbox()` SHALL return the next-highest-confidence word

#### Scenario: Sort by position
- **WHEN** `sort_by_position()` is called
- **THEN** `get_first_bbox()` SHALL return the first word in reading order

### Requirement: Canvas supports middle-click drag panning

The Canvas SHALL allow the user to pan the view by middle-clicking and dragging.

#### Scenario: Middle-click drag
- **WHEN** middle mouse button is pressed on the canvas
- **AND** the mouse is moved while holding
- **THEN** the view SHALL pan in the direction of mouse movement

### Requirement: Canvas supports scroll zoom

The Canvas SHALL allow zooming via the scroll wheel, centered on the cursor position.

#### Scenario: Scroll up zooms in
- **WHEN** a scroll-up event occurs
- **THEN** the zoom level SHALL double

#### Scenario: Scroll down zooms out
- **WHEN** a scroll-down event occurs
- **THEN** the zoom level SHALL halve

### Requirement: Canvas removes GooCanvas dependency

The Canvas SHALL NOT import from `GooCanvas` or `gi.repository.GooCanvas`.

#### Scenario: No GooCanvas import
- **WHEN** `canvas.py` is imported
- **THEN** no `GooCanvas` module SHALL be used by the Canvas or Bbox classes

### Requirement: Canvas selection rectangle stays aligned with the scene

The Canvas SHALL render its selection rectangle in widget coordinates that
apply the same image-to-widget transform as the rendered scene: the pan offset
SHALL be scaled by the zoom level, so that a given selection rectangle occupies
the same widget position as the same rectangle drawn by the ImageView at any
zoom and offset.

#### Scenario: Selection aligned at zoom above 1
- **WHEN** the zoom is 2.0
- **AND** the offset is (100, 50)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position
  ((500 + 100) * 2, (300 + 50) * 2) with size (100 * 2, 40 * 2)

#### Scenario: Selection aligned at zoom 1
- **WHEN** the zoom is 1.0
- **AND** the offset is (100, 50)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position (600, 350) with
  size (100, 40), matching the ImageView

#### Scenario: Selection aligned when offset is zero
- **WHEN** the zoom is 2.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position (1000, 600) with
  size (200, 80)

### Requirement: Canvas matches the ImageView resolution and display transform

The Canvas SHALL apply the same non-uniform image-to-widget transform as the
`ImageView`: the x axis SHALL be divided by the resolution ratio (x-resolution
over y-resolution) and both axes SHALL be divided by the display scale factor.
This SHALL apply to the OCR bounding boxes and the selection rectangle, and to
every widget-to-image coordinate conversion, so the Canvas content overlays the
scanned image exactly at any zoom, offset, resolution, and display scale.

#### Scenario: Non-square resolution ratio scales the x axis
- **WHEN** the resolution ratio is 0.5
- **AND** the zoom is 1.0 and the display scale factor is 1.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (10, 20, 30, 40)
- **THEN** the selection SHALL be rendered at widget position (20, 20) with
  size (60, 40) — x coordinates doubled, y unchanged

#### Scenario: HiDPI scale factor shrinks both axes
- **WHEN** the display scale factor is 2.0
- **AND** the resolution ratio is 1.0 and the zoom is 1.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (10, 20, 30, 40)
- **THEN** the selection SHALL be rendered at widget position (5, 10) with size
  (15, 20)

#### Scenario: Widget-to-image conversion is the inverse transform
- **WHEN** the resolution ratio is 0.5 and the display scale factor is 2.0
- **AND** the zoom is 1.0 and the offset is (0, 0)
- **AND** a user drags in the widget from (10, 5) to (70, 15)
- **THEN** the resulting image-coordinate selection SHALL be (10, 10, 60, 20)

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

### Requirement: Confidence colours retain their requested components

The colour conversion used for confidence-coloured boxes and text SHALL
preserve the requested red, green, blue and alpha components on every
supported PyGObject version. An opaque input colour SHALL remain fully opaque.

#### Scenario: Fully saturated red is preserved

- **WHEN** the canvas requests an opaque fully saturated red colour
- **THEN** the resulting colour SHALL have red 1, green 0, blue 0 and alpha 1

#### Scenario: Confidence colours remain visible on PyGObject 3.42

- **WHEN** max_color is black and min_color is red on PyGObject 3.42
- **AND** a word has confidence below min_confidence
- **THEN** the word SHALL be drawn in opaque red
- **AND** it SHALL NOT be drawn transparently
