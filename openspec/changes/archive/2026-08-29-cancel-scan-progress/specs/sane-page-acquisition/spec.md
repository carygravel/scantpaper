## MODIFIED Requirements

### Requirement: User cancel terminates the session
When the user cancels a scan, the device session SHALL be terminated promptly:
a page transfer already in progress SHALL be interrupted rather than allowed
to run to completion, and scan requests that have not yet started SHALL be
dropped.

#### Scenario: Cancel during a page transfer
- **WHEN** the user presses cancel while a page is being transferred
- **THEN** the device session SHALL be terminated promptly and the transfer
  SHALL be interrupted
- **AND** the partial page SHALL NOT be added to the document

#### Scenario: Cancel drops queued pages
- **WHEN** the user presses cancel while scan requests for further pages are
  queued and not yet started
- **THEN** the queued requests SHALL be dropped
- **AND** the requester of each dropped request SHALL be notified that the
  request was cancelled

#### Scenario: Deliberate cancel is not an error
- **WHEN** the user presses cancel and the interrupted transfer reports a
  cancelled status
- **THEN** the application SHALL NOT present the interruption to the user as
  an error
- **AND** pages acquired before the cancel SHALL remain in the document

#### Scenario: Device reusable after cancel
- **WHEN** a scan is cancelled while it is running
- **AND** the user subsequently starts a new scan batch
- **THEN** the new batch SHALL acquire pages successfully