# hocr-text-layer Specification

## Purpose

Lets users export a page's corrected text layer as hOCR and import it back into
the same or a rebuilt session, including documents where some pages have no
OCR.

## Requirements

### Requirement: Import hOCR into selected or all pages

The application SHALL provide a main-menu action that applies an hOCR file to
the selected pages or to all pages. Target pages SHALL be taken in document
order. The file SHALL be parsed into one hOCR page per `ocr_page` element, in
file order.

#### Scenario: Import into selected pages

- **WHEN** the user selects three pages and imports an hOCR file containing
  three `ocr_page` elements
- **THEN** the first, second, and third hOCR pages are applied to the first,
  second, and third selected pages, respectively

#### Scenario: Import into all pages

- **WHEN** the user chooses the all-pages range and imports an hOCR file whose
  page count matches the document
- **THEN** every page receives the hOCR page at the same position

#### Scenario: Action unavailable with no pages

- **WHEN** the document has no pages
- **THEN** the import action is insensitive

### Requirement: Import requires one hOCR page per target page

The import SHALL proceed only when the number of `ocr_page` elements equals the
number of target pages. Otherwise it SHALL change no page and SHALL show an
error naming the number of hOCR pages and the number of target pages.

#### Scenario: Fewer hOCR pages than target pages

- **WHEN** the file contains fewer `ocr_page` elements than there are target
  pages
- **THEN** no page's text layer changes
- **AND** an error reports both counts

#### Scenario: More hOCR pages than target pages

- **WHEN** the file contains more `ocr_page` elements than there are target
  pages
- **THEN** no page's text layer changes
- **AND** an error reports both counts

#### Scenario: File contains no hOCR page

- **WHEN** the chosen file contains no `ocr_page` element
- **THEN** no page's text layer changes
- **AND** an error reports that the file contains no hOCR pages

### Requirement: Import requires matching page geometry

Each hOCR page's page box SHALL have its origin at `(0, 0)` and its width and
height SHALL differ from the target page's pixel width and height by no more
than one pixel. If any page box differs by more than one pixel, the import
SHALL change no page and SHALL show an error identifying the page and both
sizes.

#### Scenario: Page dimensions match

- **WHEN** every hOCR page box is `0 0 <width> <height>` for the corresponding
  target page
- **THEN** the import proceeds

#### Scenario: One-pixel difference is accepted

- **WHEN** an hOCR page box is `0 0 2480 3506` and the target page is
  `2480 x 3507`
- **THEN** the import proceeds

#### Scenario: Page dimensions differ by more than one pixel

- **WHEN** an hOCR page box differs from its target page's pixel dimensions by
  more than one pixel
- **THEN** no page's text layer changes
- **AND** an error identifies the page and both sizes

### Requirement: Import failures show their reason

When an hOCR import is rejected, the error dialog SHALL display the reason,
such as the page count mismatch, the page dimensions, or a parse failure. It
SHALL NOT show an empty message.

#### Scenario: Geometry rejection shows both sizes

- **WHEN** an import is rejected because a page box differs by more than one
  pixel
- **THEN** the error dialog names the page and both sizes

#### Scenario: Count rejection shows both counts

- **WHEN** an import is rejected because the hOCR page count differs from the
  target page count
- **THEN** the error dialog names both counts

#### Scenario: Parse rejection names the file

- **WHEN** an import is rejected because the file cannot be parsed as hOCR
- **THEN** the error dialog names the file and the parse failure

### Requirement: Import replaces only the text layer

On success, each target page's text layer SHALL become the text of the
corresponding hOCR page. The page's stored image, image id, annotations,
resolution, and position in the document SHALL remain unchanged.

#### Scenario: Text is imported

- **WHEN** a page and its matching hOCR page contain the same words
- **THEN** the page's text layer contains those words at the hOCR page's
  bounding boxes

#### Scenario: Image and annotations are untouched

- **WHEN** the import completes on a page that has an image and annotations
- **THEN** the page keeps the same image id and image bytes
- **AND** the page's annotations are unchanged

#### Scenario: Page order is unchanged

- **WHEN** the import completes on several pages
- **THEN** the pages remain in their original document order

### Requirement: An hOCR page with no text imports as an empty text layer

When an hOCR page contains no words or text, the target page's text layer SHALL
become empty. This SHALL clear any text layer the target page had before the
import, and undo SHALL restore it.

#### Scenario: Empty page box clears the text layer

- **WHEN** the target page has text and the matching hOCR page contains an
  empty page box
- **THEN** the target page has an empty text layer after the import

#### Scenario: Undo restores the cleared text layer

- **WHEN** an import cleared a page's text layer and the user undoes the import
- **THEN** the page's previous text layer is restored

### Requirement: Import is one undoable action

The whole import SHALL be recorded as one undo step. Undo SHALL restore every
target page's text layer to its state before the import, and redo SHALL apply
the imported text layers again.

#### Scenario: One undo reverts all pages

- **WHEN** the user imports hOCR into several pages and triggers undo once
- **THEN** every target page's previous text layer is restored

#### Scenario: Redo reapplies all pages

- **WHEN** the user undoes an import and triggers redo once
- **THEN** every target page receives its imported text layer again

### Requirement: Import is atomic when cancelled or rejected

The import SHALL run in the background and SHALL support cancellation. If it is
cancelled, or rejected because of a page-count, geometry, or parse error, no
target page's text layer SHALL change.

#### Scenario: Cancel leaves the document unchanged

- **WHEN** the user cancels an import before it completes
- **THEN** no target page's text layer changes

#### Scenario: Malformed file leaves the document unchanged

- **WHEN** the chosen file cannot be parsed as hOCR
- **THEN** no target page's text layer changes
- **AND** an error reports that the file is not valid hOCR

### Requirement: Combined hOCR export contains every selected page

Saving selected pages as hOCR SHALL produce one hOCR document containing
exactly one `ocr_page` element per selected page, in document order. Pages with
a text layer SHALL contain their words as before. Pages with no text layer
SHALL be emitted as an `ocr_page` whose page box is `0 0 <width> <height>` and
which contains no words.

#### Scenario: Mixed pages with and without OCR

- **WHEN** the user saves a selection that mixes pages with OCR and pages
  without OCR as hOCR
- **THEN** the file contains one `ocr_page` per selected page
- **AND** each page without OCR has an empty page box with that page's
  dimensions

#### Scenario: All selected pages lack OCR

- **WHEN** the user saves a selection in which no page has a text layer as
  hOCR
- **THEN** the file contains one empty `ocr_page` per selected page

#### Scenario: Single page with OCR

- **WHEN** the user saves one page with a text layer as hOCR
- **THEN** the file contains one `ocr_page` with that page's words

### Requirement: hOCR export and import preserve the text layer

Exporting a page's text layer and importing it into a page with the same pixel
dimensions SHALL preserve the words, their text, bounding boxes, confidence,
baseline, text angle, and ids. A page with no text layer SHALL export and
re-import as a page with no text layer.

#### Scenario: Page with OCR round-trips

- **WHEN** a page's text layer is exported to hOCR and imported into a page
  with the same pixel dimensions
- **THEN** the words, text, bounding boxes, confidence, baseline, text angle,
  and ids match the exported text layer

#### Scenario: Page without OCR round-trips

- **WHEN** a page with no text layer is exported and the file is imported into
  a page with the same pixel dimensions
- **THEN** the target page has no text layer

### Requirement: hOCR exchange is text-layer only

hOCR export SHALL include only the text layer. Import SHALL NOT add, remove, or
change annotations or images. A page's annotations SHALL remain exactly as they
were before an import.

#### Scenario: Annotations are not exported

- **WHEN** a page with annotations is saved as hOCR
- **THEN** the hOCR file contains no annotation content
- **AND** the page's annotations remain in the document

#### Scenario: Annotations survive an import

- **WHEN** an import completes on a page with annotations
- **THEN** the page's annotations are unchanged
