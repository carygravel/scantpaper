## Purpose

Defines how scantpaper acquires pages from SANE devices: how the device
session is managed across multi-page scan batches, when the session is
terminated between pages versus at batch end, how end-of-batch is
detected, and how a requested colour depth is honoured at acquisition.
Correct session handling determines whether drivers that capture
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

### Requirement: Requested colour depth is honoured

When 1-bit output is requested - by depth or by an equivalent bilevel scan
mode (Lineart, Binary, Black & White, Halftone or Error Diffusion) - and the
device delivers a deeper frame, scantpaper SHALL convert it to 1-bit before
importing it, using the threshold tool's colour-aware semantics (an
ink-strength cutoff at the configured threshold). Frames delivered at the
requested depth, or when 1-bit output is not requested, SHALL be imported
unconverted.

#### Scenario: Backend delivers 8-bit despite a 1-bit request

- **WHEN** the scan options request a depth of 1 bit and the device delivers an
  8-bit frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the
  colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the
  requested depth

#### Scenario: Bilevel scan mode delivered deeper than requested

- **WHEN** the scan options request a bilevel scan mode such as Lineart and the
  device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the
  colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the
  requested depth

#### Scenario: Bilevel scan mode honoured

- **WHEN** the scan options request a bilevel scan mode and the device delivers
  a 1-bit frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Continuous-tone scan mode leaves deeper frames untouched

- **WHEN** the scan options request a grayscale or colour scan mode and the
  device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Backend honours the 1-bit request

- **WHEN** the scan options request a depth of 1 bit and the device delivers a
  1-bit frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: No 1-bit request leaves deeper frames untouched

- **WHEN** the scan options do not request a 1-bit depth or bilevel scan mode
  and the device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Colour frame despite a 1-bit request

- **WHEN** the scan options request 1-bit output and the device delivers a
  colour frame containing coloured content distinct from the paper
- **THEN** the converted 1-bit page SHALL render that coloured content as ink,
  per the colour-aware threshold semantics

### Requirement: Deeper frames are reported without blocking a batch

The application SHALL inform the user that the device did not deliver the
requested depth. The notification SHALL be non-blocking, so that a multi-page
batch is not interrupted by repeated dialogs.

#### Scenario: Notification does not block a batch

- **WHEN** several pages in one batch are delivered deeper than requested
- **THEN** each page SHALL still be imported as a 1-bit image
- **AND** the user SHALL NOT be presented with a modal dialog for each page

### Requirement: A feeder-empty batch end is not reported as an error

When a scan batch ends because the driver reports that the feeder has no
documents left, the application SHALL record that as a normal end-of-batch
event at INFO level, without an exception traceback, and SHALL NOT emit an
error-level record for it. The batch SHALL still end and keep the pages
already acquired.

#### Scenario: Empty feeder ends the batch quietly

- **WHEN** the driver reports that the document feeder is out of documents
  during a scan batch
- **THEN** the application SHALL NOT emit an error-level log record or a
  traceback for that event
- **AND** it SHALL record the end of batch at INFO level
- **AND** the pages already acquired in the batch SHALL be kept

### Requirement: Genuine device errors stay errors

A scan failure that is not the feeder-empty status and not a transfer
deliberately cancelled by the user SHALL still be logged at ERROR level with
its traceback, and SHALL still be reported to the user.

#### Scenario: Device error mid-batch remains an error

- **WHEN** the driver raises an error other than the feeder-empty status
  during a scan batch, and the user has not cancelled
- **THEN** the application SHALL emit an error-level log record with a
  traceback
- **AND** the error SHALL still be reported to the user
