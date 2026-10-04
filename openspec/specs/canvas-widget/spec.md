# Canvas Widget

## Purpose

Provide a Cairo-based rendering widget for displaying and interacting with OCR bounding boxes and text overlaid on scanned document images.

## Requirements

### Requirement: Canvas renders OCR bounding boxes and text

The Canvas widget SHALL render a scene graph of OCR elements (page, carea, paragraph, line, word) as colored bounding rectangles with rotated text. When the text of an element in the scene graph changes, the Canvas SHALL redraw that element with its new text on the next frame.

#### Scenario: Single word displayed
- **WHEN** `set_text()` is called with a single word bbox at (10, 20, 100, 40) with text "hello"
- **THEN** the canvas SHALL display a rectangle from (10, 20) to (100, 40) and the text "hello" centered within it

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
- **THEN** the rendered text SHALL be rotated 90 degrees within its bounding box

#### Scenario: Multiple words on same line
- **WHEN** `set_text()` is called with two words on the same line (depth 3) with different x positions
- **THEN** both words SHALL be displayed at their respective positions with correct bounding boxes

#### Scenario: Changed text is redrawn
- **WHEN** a word's text is changed after it has already been drawn at least once
- **THEN** the next drawn frame SHALL show the new text for that word
- **AND** SHALL NOT show the text the word had before the change

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

The Canvas SHALL support an offset property that controls which portion of the scene is visible, clamped to prevent viewing outside the image bounds. The offset SHALL use the same sign convention as ImageView: a positive offset shifts the image rightward in widget space.

#### Scenario: Offset set within bounds
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset` is set to (100, 200)
- **THEN** the canvas SHALL scroll so that the image pixel (100, 200) aligns with the widget origin

#### Scenario: Offset clamped to prevent edge visibility
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset.x` is set to -50
- **THEN** `offset.x` SHALL be clamped to 0

#### Scenario: offset-changed signal
- **WHEN** `offset` changes to a new value
- **THEN** the "offset-changed" signal SHALL be emitted with (x, y) integers

#### Scenario: Offset matches ImageView convention
- **WHEN** offset is set on the ImageView
- **THEN** the same offset value SHALL produce the same image-visible-region on both widgets

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
