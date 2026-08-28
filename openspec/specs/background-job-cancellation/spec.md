# background-job-cancellation

## Purpose

Lets users cancel running or queued background work — importing files, saving exports, and document post-processing — so the application stops promptly, leaves the document in a consistent state, and remains usable for further operations.

## Requirements

### Requirement: Cancel stops running and queued jobs
When the user activates Cancel on a progress bar that is reporting background work, the application SHALL cancel that work: jobs that are queued but have not started SHALL be dropped, and the currently running job SHALL be stopped as soon as practical. The progress bar SHALL be hidden.

#### Scenario: Cancel during a bulk import
- **WHEN** the user imports multiple files and activates Cancel before the import completes
- **THEN** no further files are imported
- **AND** the progress bar is hidden
- **AND** the pages imported before the cancel remain in the document

#### Scenario: Cancel during a save
- **WHEN** the user activates Cancel while a PDF, DjVu, TIFF, image, text, or hOCR save is running
- **THEN** the save is stopped
- **AND** no partially-written output is presented as a completed export
- **AND** the progress bar is hidden

### Requirement: Spawned subprocesses are terminated on cancel
When a job is cancelled, any subprocess spawned for that job — image extraction, conversion, merging, or hook commands — SHALL be terminated rather than being allowed to run to completion in the background.

#### Scenario: Cancel while a conversion subprocess runs
- **WHEN** the user cancels a long-running save while its conversion subprocess is still executing
- **THEN** the subprocess is terminated
- **AND** the job finishes without committing its output

### Requirement: Application remains usable after cancel
After a job is cancelled, the background thread SHALL accept and process new work, and the document SHALL reflect only the pages that actually exist before the cancel was requested.

#### Scenario: Save after cancel
- **WHEN** the user cancels a PDF save and then saves a single page as an image
- **THEN** the image save completes successfully and produces a valid file

#### Scenario: Page count unchanged by cancelled work
- **WHEN** the user cancels an import mid-way
- **THEN** the document contains exactly the pages imported before the cancel and no partial pages from the cancelled job