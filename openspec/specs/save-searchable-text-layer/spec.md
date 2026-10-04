# Save Searchable Text Layer

## Purpose

Defines the requirement that a PDF saved by scantpaper carries a searchable
text layer for every page that has one, so text in the saved output can be
selected, copied, and searched just as it could in the source.

## Requirements

### Requirement: Saved PDF retains a searchable text layer
When scantpaper saves a PDF and a page has a text layer, the output PDF SHALL
contain a searchable text layer for that page that reproduces the words of the
text layer being saved, positioned according to that text layer's geometry.

The hOCR structure that scantpaper emits for a page SHALL include the container
levels (`ocr_par`/`ocr_line`) that a PDF text-layer renderer walks, so that
pages whose text layer has no explicit paragraph or line structure still produce
a rendered, extractable text layer.

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
