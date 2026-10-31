# Spec Delta

## MODIFIED Requirements

### Requirement: Cancel stops running and queued jobs
When the user activates Cancel on a progress bar that is reporting background
work, the application SHALL cancel that work: jobs that are queued but have
not started SHALL be dropped, and the currently running job SHALL be stopped
as soon as practical. The progress bar SHALL be hidden. This includes
follow-up work that a completed job would otherwise register after the
cancel, such as the next page of a scan batch.

#### Scenario: Cancel during a bulk import
- **WHEN** the user imports multiple files and activates Cancel before the
  import completes
- **THEN** no further files are imported
- **AND** the progress bar is hidden
- **AND** the pages imported before the cancel remain in the document

#### Scenario: Cancel during a save
- **WHEN** the user activates Cancel while a PDF, DjVu, TIFF, image, text, or
  hOCR save is running
- **THEN** the save is stopped
- **AND** no partially-written output is presented as a completed export
- **AND** the progress bar is hidden

#### Scenario: Cancel between scan pages
- **WHEN** the user cancels a scan batch after one page has completed but
  before the next page starts
- **THEN** no further page from that batch is acquired or imported
- **AND** the progress bar is hidden
- **AND** the completed page remains in the document

### Requirement: Application remains usable after cancel
After a job is cancelled, the background thread SHALL accept and process new
work, and the document SHALL reflect only the pages that actually exist
before the cancel was requested.

#### Scenario: Save after cancel
- **WHEN** the user cancels a PDF save and then saves a single page as an
  image
- **THEN** the image save completes successfully and produces a valid file

#### Scenario: Page count unchanged by cancelled work
- **WHEN** the user cancels an import mid-way
- **THEN** the document contains exactly the pages imported before the cancel
  and no partial pages from the cancelled job

#### Scenario: Scan after cancelling a flatbed batch
- **WHEN** the user cancels a flatbed scan batch and then starts a new scan
- **THEN** the new batch acquires pages successfully
- **AND** the document contains only the pages acquired before the cancel
