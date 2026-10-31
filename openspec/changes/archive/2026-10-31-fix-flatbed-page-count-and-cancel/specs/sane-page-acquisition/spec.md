# Spec Delta

## MODIFIED Requirements

### Requirement: User cancel terminates the session
When the user cancels a scan, the device session SHALL be terminated promptly:
a page transfer already in progress SHALL be interrupted rather than allowed
to run to completion, and scan requests that have not yet started SHALL be
dropped. A page whose transfer completed before the cancel SHALL still be
imported, and no further page of the cancelled batch SHALL be acquired or
queued after the cancel.

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

#### Scenario: Cancel between pages does not queue the next page
- **WHEN** the user cancels after a page transfer has completed but before
  the next page starts
- **THEN** the completed page SHALL remain in the document
- **AND** no further page from that batch SHALL be acquired or queued
- **AND** the batch SHALL end as cancelled, not as a completed scan

## ADDED Requirements

### Requirement: Cancel recovers a device that does not interrupt promptly

If a backend does not stop an in-flight transfer within a bounded time
after the user cancels, the application SHALL report the failure and SHALL
remain responsive. A subsequent scan batch SHALL start once the device is
available.

#### Scenario: Backend ignores cross-thread cancel
- **WHEN** the user cancels and the backend does not stop the in-flight
  transfer within the bounded time
- **THEN** the application SHALL report the failure instead of leaving the
  batch indefinitely running
- **AND** the application SHALL remain responsive
- **AND** a subsequent scan SHALL start once the device is available
