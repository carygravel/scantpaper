# save-progress-reporting

## Purpose

Governs how the post-process progress bar reports progress while a document is being saved as a PDF: which stage reports per-page progress and which stage reports a stage-level message.

## Requirements

### Requirement: Per-page progress during PDF page writing
While a PDF save is writing pages to its temporary directory, the progress bar SHALL display both the fraction of pages written and a message identifying the current page number and the total number of pages.

#### Scenario: Progress reported while writing pages
- **WHEN** a PDF save begins writing pages
- **THEN** the progress bar SHALL show the fraction of pages completed
- **AND** the progress bar SHALL display a message of the form "Writing page X of Y", where X is the current page number and Y is the total number of pages

#### Scenario: Progress advances with each page
- **WHEN** each additional page is written
- **THEN** the fraction SHALL increase and the page number in the message SHALL advance

### Requirement: Stage message during PDF conversion
While the written pages are being converted into the PDF (the img2pdf step), the progress bar SHALL display a message indicating that the PDF is being written.

#### Scenario: Conversion stage message shown
- **WHEN** page writing has finished and PDF conversion begins
- **THEN** the progress bar SHALL display a message indicating the PDF is being written

### Requirement: Per-page progress stops after conversion
The per-page progress messages ("Writing page X of Y") SHALL only be reported while pages are being written, and SHALL NOT be reported after the PDF conversion step has run.

#### Scenario: No per-page progress after conversion
- **WHEN** the PDF conversion step has completed
- **THEN** the progress bar SHALL NOT display any further "Writing page X of Y" messages
