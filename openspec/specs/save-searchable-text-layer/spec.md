# Save Searchable Text Layer

## Purpose

Defines the requirement that a PDF saved by scantpaper carries a searchable
text layer for every page that has one, so text in the saved output can be
selected, copied, and searched just as it could in the source.

## Requirements

### Requirement: Saved PDF retains a searchable text layer
When a page being saved has a text layer, the output PDF SHALL contain a
searchable text layer that reproduces its words and their positions.

The emitted hOCR SHALL include the container levels (`ocr_par`/`ocr_line`) a
PDF text-layer renderer walks, so every word is nested under a paragraph and
stays extractable. This SHALL hold for text layers with no explicit paragraph
or line structure, and for pages mixing OCR paragraphs with individually
added words outside them.

#### Scenario: Saving an imported page preserves its searchable text
- **WHEN** the user imports a PDF page, edits its text layer, and saves the
  document as a PDF
- **THEN** the output PDF SHALL contain a text layer from which the saved text
  can be extracted
- **AND** the extracted text SHALL contain the words of the saved text layer

#### Scenario: Saving a page with a flat text layer
- **WHEN** the user saves a page whose text layer contains words with no
  paragraph or line grouping
- **THEN** the output PDF SHALL still contain an extractable, searchable text
  layer for that page

#### Scenario: Saving a page with OCR paragraphs and a manually added word
- **WHEN** the user has a page whose text layer already contains OCR paragraphs
  and then adds a new word in an area outside those paragraphs
- **AND** saves the document as a PDF
- **THEN** the output PDF SHALL contain a searchable text layer
- **AND** the extracted text SHALL contain the manually added word alongside
  the OCR-recognised words

### Requirement: Rotated text is rendered at its text angle
Words with a non-horizontal effective text angle SHALL be saved at that
angle. The effective angle combines the word's own text angle with all
ancestor angles, each taken once.

A word SHALL be rendered at its own angle whether under a page, a synthetic
export line, or an existing line at a different angle. Within one line, words
with different effective angles SHALL be separated so each angle is saved
correctly.

The set and order of extracted words SHALL be unaffected by rotation.

#### Scenario: A manually rotated word is saved vertically
- **WHEN** the user adds a word, rotates it 90 degrees, and saves the page as
  a searchable PDF
- **THEN** the word in the output PDF SHALL be rendered vertically
- **AND** its text SHALL remain extractable
- **AND** its rendered position SHALL sit inside the slice's saved bounding
  box rather than spilling down the page

#### Scenario: A rotated word inside an unrotated OCR line is saved vertically
- **WHEN** a word with a 90-degree text angle is nested in an existing OCR
  line whose text angle is 0
- **AND** the page is saved as a searchable PDF
- **THEN** the rotated word SHALL be rendered vertically in the output PDF
- **AND** the other words on that line SHALL remain horizontal

#### Scenario: Ancestor rotation is applied exactly once
- **WHEN** a word inherits a 90-degree rotation from an ancestor and carries
  no additional rotation of its own
- **AND** the page is saved as a searchable PDF
- **THEN** the word SHALL be rendered 90 degrees from horizontal in the output
  PDF
- **AND** the rotation SHALL NOT be applied twice

#### Scenario: Unrotated text is unchanged
- **WHEN** a page whose words all have an effective angle of 0 is saved as a
  searchable PDF
- **THEN** every word SHALL be rendered horizontally as before
- **AND** the extracted word set and order SHALL be unchanged

### Requirement: Text layer survives a save round trip
When a page's text layer is exported for saving and then read back from the
saved PDF, the set of words SHALL match the text layer being saved, and their
positions SHALL correspond to the text layer geometry so that text appears at
its correct location.

#### Scenario: Word set is preserved
- **WHEN** the user saves a page with a text layer and extracts the text from
  the saved PDF
- **THEN** every word in the saved text layer SHALL be present in the extracted
  text

#### Scenario: Text appears at its expected location
- **WHEN** the user saves a page with a text layer and inspects the rendered
  text positions in the saved PDF
- **THEN** the words SHALL be positioned according to the saved text layer
  geometry rather than collapsed to a single point

### Requirement: Synthetic line grouping preserves word geometry

When a flat text layer with no line structure is wrapped into synthetic
`ocr_line` elements for saving, words SHALL be grouped so that one word's
size cannot distort another word's rendering. A tall word (such as a
rotated slice) SHALL NOT pull upright words that sit on different rows
into a single synthetic line, because the renderer derives a line's font
size from its bounding box.

#### Scenario: Mixed-angle flat layer keeps upright rows separate

- **WHEN** a flat text layer contains upright words across several rows
  and at least one rotated word taller than an upright word
- **AND** the page is saved as a searchable PDF
- **THEN** the upright words SHALL be grouped into one synthetic line per
  row
- **AND** each upright word SHALL be rendered at a height comparable to its
  own bounding box rather than the taller rotated word's

#### Scenario: Equal-height words on one row still share a line

- **WHEN** a flat text layer contains upright words whose vertical centres
  are aligned on one row
- **THEN** those words SHALL be grouped into a single synthetic line
- **AND** that line's bounding box SHALL enclose only those words

#### Scenario: Spaced rotated words each keep their own line

- **WHEN** a flat text layer contains rotated words spaced apart along
  their reading direction
- **THEN** each rotated word SHALL form its own synthetic line
- **AND** each such line SHALL carry the word's text angle
