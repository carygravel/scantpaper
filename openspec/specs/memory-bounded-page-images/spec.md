# memory-bounded-page-images Specification

## Purpose

Governs how full-size page image data is held in memory: images decode
only when a consumer needs their pixels and are released after use, so
documents with many high-resolution pages do not require keeping every
image decoded at once and large PDF saves complete within available
memory.

## Requirements

### Requirement: Page images are decoded only on demand
Loading a page or constructing its record SHALL NOT decode the page's
full-size image from its stored form. The image SHALL be decoded only when
a consumer requests the page's pixel data. A later request for pixel data
on a page that already holds decoded pixels SHALL NOT cause the image to be
decoded again.

#### Scenario: Loading a page for its text layer
- **WHEN** a page is loaded and only its text layer or metadata are read
- **THEN** the page's full-size image SHALL NOT be decoded

#### Scenario: Loading a page for verbatim PDF embedding
- **WHEN** a page is loaded to save its unmodified stored image into a PDF
  verbatim
- **THEN** the page's full-size image SHALL NOT be decoded

#### Scenario: A consumer requests pixel data
- **WHEN** a consumer needs the page's pixels, such as OCR, displaying the
  page, or re-encoding it
- **THEN** the image SHALL be decoded
- **AND** a later request for the same page's pixels SHALL reuse the
  decoded data without decoding the image again

### Requirement: Saving releases each page's image after use
When the application saves multiple pages to a PDF, each page's in-memory
image data SHALL be released once that page's contribution to the output
has been written, and SHALL NOT be retained for the rest of the save. The
memory occupied by page image data during the save SHALL NOT accumulate
proportionally to the number of pages. Releasing a page's image SHALL NOT
discard the page's text layer, annotations, or other metadata.

#### Scenario: Verbatim JPEG pages saved
- **WHEN** the user saves a document whose pages are unmodified JPEG images
  that the save embeds verbatim
- **THEN** each page's image data SHALL be released after its temporary
  file is written
- **AND** the save SHALL complete with page-image memory that does not grow
  with the page count

#### Scenario: Pages re-encoded during save
- **WHEN** a page must be re-encoded during save, such as when downsampling
  or using a non-JPEG compression, so the encoding needs the page's pixels
- **THEN** the image SHALL be decoded for the encoding and released once
  the encoding is complete

#### Scenario: Text layer used after image release
- **WHEN** the save writes a page's searchable text layer into the PDF
  after that page's image content has been released
- **THEN** the text layer and its position data SHALL still be available
  and SHALL be embedded correctly in the output

### Requirement: Large documents save within bounded memory
The application SHALL be able to save a multi-page document to PDF when the
combined decoded size of all its pages exceeds available memory, provided
the working set of a single page (one decoded image together with the
in-flight pipeline data) fits in memory. During a PDF save the page images
SHALL be decoded and released one page at a time, so that peak memory used
for page images does not scale with the number of pages.

#### Scenario: Many high-resolution pages
- **WHEN** a document has hundreds of high-resolution pages whose combined
  decoded size exceeds available memory and each page could be saved on its
  own
- **THEN** the save SHALL complete
- **AND** the application SHALL continue running rather than being
  terminated for exhausting memory

#### Scenario: One page at a time
- **WHEN** the application saves a multi-page document
- **THEN** the peak memory used for page images SHALL be approximately the
  working set of a single page rather than of all pages combined
