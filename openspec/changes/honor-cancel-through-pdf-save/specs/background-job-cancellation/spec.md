# Spec Delta

## MODIFIED Requirements

### Requirement: Cancel stops running and queued jobs

When the user activates Cancel on a progress bar that is reporting background
work, the application SHALL cancel that work: jobs that are queued but have
not started SHALL be dropped, and the currently running job SHALL be stopped
as soon as practical. The progress bar SHALL be hidden.

A running PDF save SHALL be stopped at whichever phase the cancel lands,
including after its pages have been assembled while the text layer is being
embedded or the PDF finalized, and the save SHALL NOT report a completed
export afterwards.

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

#### Scenario: Cancel lands after page assembly

- **WHEN** the user activates Cancel while a PDF save has finished assembling
  its pages and is embedding the text layer
- **THEN** the save SHALL be stopped
- **AND** the save SHALL NOT report the export as completed
- **AND** the progress bar SHALL be hidden

#### Scenario: Cancel between scan pages

- **WHEN** the user cancels a scan batch after one page has completed but
  before the next page starts
- **THEN** no further page from that batch is acquired or imported
- **AND** the progress bar is hidden
- **AND** the completed page remains in the document

### Requirement: Cancelled job requests notify their requester

When a background job request is dropped or interrupted by a cancel, the
requester SHALL be notified that the request was cancelled rather than
receiving no response, and a cancelled request SHALL NOT also complete as
finished or error.

#### Scenario: Queued job reports cancelled

- **WHEN** a job request is queued but has not yet started
- **AND** the user cancels the work that owns the request
- **THEN** the request's cancelled callback SHALL be invoked
- **AND** the request's finished callback SHALL NOT be invoked

#### Scenario: Interrupted job reports cancelled

- **WHEN** a running job's underlying work is interrupted by a cancel
- **THEN** the request's cancelled callback SHALL be invoked
- **AND** the request's finished callback SHALL NOT be invoked
- **AND** the request's error callback SHALL NOT be invoked
- **AND** the partial output of the interrupted job SHALL NOT be presented as
  completed
