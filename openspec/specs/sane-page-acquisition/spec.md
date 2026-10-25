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
