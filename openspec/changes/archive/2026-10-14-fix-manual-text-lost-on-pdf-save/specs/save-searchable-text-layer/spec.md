## MODIFIED Requirements

### Requirement: Saved PDF retains a searchable text layer
When scantpaper saves a PDF and a page has a text layer, the output PDF SHALL
contain a searchable text layer for that page that reproduces the words of the
text layer being saved, positioned according to that text layer's geometry.

The hOCR structure that scantpaper emits for a page SHALL include the container
levels (`ocr_par`/`ocr_line`) that a PDF text-layer renderer walks, so that
every word in the text layer is nested under a paragraph and therefore rendered
and extractable. This SHALL hold for pages whose text layer has no explicit
paragraph or line structure, and SHALL also hold for pages that mix automatic
OCR paragraphs with individually added words that are not themselves inside a
paragraph.

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
