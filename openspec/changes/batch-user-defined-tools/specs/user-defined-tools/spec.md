## Purpose

Lets users apply an external command (a "user-defined tool") to the pages of a
document, either one page at a time or to all selected pages in a single
invocation so long-lived GUI tools can open every image at once.

## ADDED Requirements

### Requirement: Apply a user-defined tool to pages
The system SHALL run a user-defined command on selected pages. By default the
command runs once per page, with `%i` substituted by the path of a temporary
input file holding the page image and `%o` substituted by the path of a
temporary output file the tool must write. When the command contains no `%o`,
the tool may edit its input in place and the modified file SHALL become the
new page contents.

#### Scenario: Tool with %i and %o output
- **WHEN** the user applies a tool command containing both `%i` and `%o` to a
  page
- **THEN** the page image is written to a temporary `%i` file, the tool is run
  to write the `%o` file
- **AND** the page is replaced by the contents of the `%o` file on completion

#### Scenario: Tool without %o edits in place
- **WHEN** the user applies a tool command containing `%i` but no `%o`
- **THEN** the page is copied to a temporary working file that is passed as
  `%i`
- **AND** if the tool modified that working file, the page is replaced by its
  contents

#### Scenario: Page properties survive the tool run
- **WHEN** a page is replaced after a user-defined tool run
- **THEN** the page's resolution, OCR text layer, and page position are
  preserved
- **AND** the document is marked as no longer saved

### Requirement: Batch mode passes all selected pages to one invocation
The system SHALL offer a batch mode in which all selected pages are passed to a
single invocation of the tool. In batch mode `%i` SHALL be substituted by the
path of each page's temporary working file, space-separated, so that a tool
such as `gimp %i` opens every selected image at the same time.

#### Scenario: All selected images open together
- **WHEN** the user enables batch mode and applies a tool with `%i` to 5
  selected pages
- **THEN** a single invocation of the tool is started with all 5 working file
  paths substituted for `%i`
- **AND** the application waits only for that single invocation to finish

#### Scenario: Batch mode runs only one process per selection
- **WHEN** batch mode is enabled
- **THEN** the number of tool processes started equals the number of batches
  (one), not the number of selected pages

#### Scenario: Batch mode with %o is rejected
- **WHEN** the user enables batch mode for a tool command that contains `%o`
- **THEN** the application reports an error and does not start the tool

### Requirement: Batch copy-back replaces only modified pages
After a batch run completes, the system SHALL read back each page's working
file. A working file that was modified SHALL replace its corresponding page;
an unmodified working file SHALL leave its page untouched. Page order SHALL be
preserved.

#### Scenario: Modified and unmodified inputs in one batch
- **WHEN** a batch tool run finishes having modified pages 2 and 4 of 5 but
  left pages 1, 3, and 5 untouched
- **THEN** pages 2 and 4 are replaced by the modified working files
- **AND** pages 1, 3, and 5 are unchanged
- **AND** the pages remain in their original order

### Requirement: Batch errors are reported once per batch
If a batch tool invocation fails, the system SHALL report a single error naming
the batch rather than one error per page.

#### Scenario: Tool exits with failure
- **WHEN** the batch tool exits with a nonzero status
- **THEN** the application shows one error for the batch
- **AND** no page is replaced from the failed run

#### Scenario: Batch produces no modified files
- **WHEN** the batch tool exits successfully but has written no modified files
- **THEN** the application reports that no pages were modified
- **AND** all pages remain unchanged

### Requirement: Batch progress and cancellation
The batch SHALL be reported as a single job in the progress reporting UI and
SHALL be cancellable.

#### Scenario: Progress reflects one batch job
- **WHEN** a batch run is in progress
- **THEN** the progress reporting treats the whole batch as one queued,
  started, running, and finished job

#### Scenario: Cancelling a batch
- **WHEN** the user cancels an in-progress batch run
- **THEN** the tool process is terminated
- **AND** no page is replaced from the cancelled run