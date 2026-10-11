## MODIFIED Requirements

### Requirement: Canvas renders OCR bounding boxes and text

The Canvas widget SHALL render a scene graph of OCR elements (page, carea, paragraph, line, word) as colored bounding rectangles with rotated text. When the text of an element in the scene graph changes, the Canvas SHALL redraw that element with its new text on the next frame.
When drawing text over the scanned image, the Canvas SHALL align the rendered text by its baseline to the baseline position derived from the hOCR `baseline` attribute (respecting rotation and slope) rather than vertically centering the rendered text's ink box in the bounding box.

#### Scenario: Single word displayed
- **WHEN** `set_text()` is called with a single word bbox at (10, 20, 100, 40) with text "hello" and hOCR baseline information
- **THEN** the canvas SHALL display a rectangle from (10, 20) to (100, 40) and the text "hello" positioned so its baseline aligns with the baseline derived from the hOCR data

#### Scenario: Text inside bounding box is rotated
- **WHEN** a word has textangle 90
- **THEN** the rendered text SHALL be rotated 90 degrees within its bounding box and positioned according to its baseline

#### Scenario: Baseline alignment for words with descenders
- **WHEN** rendering a word that contains descender characters (e.g., "jumps", "quick", "happy") using its hOCR baseline
- **THEN** the rendered text SHALL be vertically positioned using baseline alignment so that descenders extend below the baseline in a manner consistent with the hOCR's baseline coordinate system

#### Scenario: Baseline alignment for words without descenders
- **WHEN** rendering a word with no descender characters (e.g., "man", "run", "sun") using its hOCR baseline
- **THEN** the rendered text SHALL be vertically positioned using baseline alignment to match the baseline position from hOCR, avoiding the vertical shift that occurs with pure vertical centering of the ink box
