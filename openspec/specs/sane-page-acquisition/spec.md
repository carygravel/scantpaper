## Purpose

Defines how scantpaper acquires pages from SANE devices: how the device
session is managed across multi-page scan batches, when the session is
terminated between pages versus at batch end, and how end-of-batch is
detected. Correct session handling determines whether drivers that capture
or buffer pages ahead of delivery (e.g. duplex pass-through feeders) can
deliver every frame to the user, and whether backends that require closed
sessions between flatbed scans behave.

## Requirements

### Requirement: Feeder batches preserve buffered frames
While acquiring multiple pages from a document feeder within one batch, the
application SHALL NOT terminate the device session between pages,
regardless of the cancel-between-pages setting, so that drivers which read
ahead and buffer subsequent pages can deliver every captured frame.

#### Scenario: Duplex pass-through scan yields both sides
- **WHEN** one sheet is scanned in duplex mode from a feeder that captures
  both sides simultaneously and buffers them
- **THEN** both sides SHALL be imported as two separate pages

#### Scenario: Buffered frame survives until delivered
- **WHEN** the driver has buffered the next page while the current page is
  being transferred
- **THEN** the next acquisition of the same batch SHALL deliver that buffered
  page instead of discarding it

#### Scenario: Setting does not affect feeders
- **WHEN** the cancel-between-pages setting is enabled and multiple pages are
  scanned from a document feeder
- **THEN** the device session SHALL NOT be terminated between those pages

### Requirement: Flatbed batches honour the cancel-between-pages setting
When the cancel-between-pages setting is enabled, the application SHALL
terminate the device session between consecutive pages acquired from a
flatbed within one batch. When it is disabled, the session SHALL remain open
across such pages.

#### Scenario: Enabled terminates between flatbed pages
- **WHEN** two pages are scanned consecutively from a flatbed with
  cancel-between-pages enabled
- **THEN** the device session SHALL be terminated between the two
  acquisitions

#### Scenario: Disabled keeps the session open across a flatbed batch
- **WHEN** multiple pages are scanned consecutively from a flatbed with
  cancel-between-pages disabled
- **THEN** the device session SHALL NOT be terminated between those pages
- **AND** the session SHALL still be terminated when the batch ends

### Requirement: Batch end terminates the session
When a scan batch finishes - because the feeder reported no more documents,
because the requested number of pages has been acquired, or because an error
occurred - the application SHALL terminate the device session, so that no
open session leaks into the next batch or device operation.

#### Scenario: Empty feeder ends the batch cleanly
- **WHEN** the driver reports no documents left during a batch
- **THEN** the batch SHALL end without showing an error dialog
- **AND** pages already acquired in the batch SHALL be kept
- **AND** the device session SHALL be terminated

#### Scenario: Page limit reached terminates the session
- **WHEN** the requested number of pages has been acquired from a feeder
- **THEN** the batch SHALL end and the device session SHALL be terminated,
  discarding any further buffered frames

#### Scenario: Mid-batch error still terminates the session
- **WHEN** a device error occurs while reading a page mid-batch
- **THEN** the error SHALL be reported to the user
- **AND** the device session SHALL be terminated

### Requirement: User cancel terminates the session
When the user cancels a scan, the device session SHALL be terminated
promptly.

#### Scenario: Cancel during a page transfer
- **WHEN** the user presses cancel while a page is being transferred
- **THEN** the device session SHALL be terminated and the partial page SHALL
  NOT be added to the document
