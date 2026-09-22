## Purpose

Allows users performing destructive book scans on a flatbed (where fronts are
scanned with the page flipped over relative to backs) to automatically
alternate the per-page rotation by parity in a single batch, so that every
page is correctly rotated without manual fix-up or re-OCR.

## ADDED Requirements

### Requirement: Flatbed batch rotation alternates by page parity
When the alternating-rotation toggle is enabled, the rotation applied to each
page of a flatbed batch SHALL alternate by parity of the page's position
within the scan batch: odd pages SHALL be rotated by the configured rotation
angle and even pages SHALL be rotated by that same angle plus 180 degrees
(modulo 360 degrees). Because a flipped page aligned to the same edge is
always rotated 180 degrees relative to its front, this alternation uprights
both sides from a single configured angle.

#### Scenario: Odd pages use the configured angle
- **WHEN** the alternating-rotation toggle is enabled, the rotation angle is
  270 degrees, and a flatbed batch of four pages is scanned
- **THEN** pages 1 and 3 SHALL be rotated by 270 degrees

#### Scenario: Even pages use the angle plus 180 degrees
- **WHEN** the alternating-rotation toggle is enabled, the rotation angle is
  270 degrees, and a flatbed batch of four pages is scanned
- **THEN** pages 2 and 4 SHALL be rotated by 90 degrees (270 + 180 modulo 360)

#### Scenario: A single configured angle uprights both sides
- **WHEN** the alternating-rotation toggle is enabled with a rotation angle of
  270 degrees for a book scan
- **THEN** every scanned front SHALL be upright after rotating 270 degrees and
  every scanned back SHALL be upright after rotating 90 degrees

### Requirement: Alternating rotation is opt-in and off by default
The alternating-rotation toggle SHALL default to off. The standard flatbed
batch behaviour (all pages use the facing rotation) SHALL remain unchanged
until the user explicitly enables the toggle.

#### Scenario: Toggle defaults to off
- **WHEN** a scan dialog is opened on a flatbed device
- **THEN** the alternating-rotation toggle SHALL be inactive

#### Scenario: Toggle off leaves all pages with the facing rotation
- **WHEN** the alternating-rotation toggle is off and a flatbed batch of more
  than one page is scanned
- **THEN** every page SHALL be rotated by the facing rotation angle

### Requirement: Toggle is bound to flatbed batch scanning
The alternating-rotation toggle SHALL be available only when a flatbed is
selected as the scan source, batch scanning from the flatbed is allowed, and
more than one page is configured for the batch. In all other configurations
the toggle SHALL NOT be shown.

#### Scenario: Hidden outside flatbed batch mode
- **WHEN** the selected source is not a flatbed, or batch scanning from the
  flatbed is not allowed, or only one page is configured
- **THEN** the alternating-rotation toggle SHALL NOT be visible

#### Scenario: Visible in flatbed batch mode
- **WHEN** a flatbed is selected, batch scanning from the flatbed is allowed,
  and more than one page is configured
- **THEN** the alternating-rotation toggle SHALL be visible

### Requirement: Alternating rotation does not affect ADF or duplex scanning
When the alternating-rotation toggle is not enabled — or when scanning from a
document feeder or in a duplex workflow — rotation SHALL be chosen solely by
the side-to-scan setting, and page-number parity SHALL NOT influence rotation.

#### Scenario: ADF batch unaffected
- **WHEN** pages are scanned from a document feeder with the
  alternating-rotation toggle off
- **THEN** every page SHALL be rotated according to the side-to-scan setting

#### Scenario: Duplex workflow unaffected
- **WHEN** a double-sided workflow is used and the alternating-rotation toggle
  is off
- **THEN** facing pages SHALL use the facing rotation and reverse pages SHALL
  use the reverse rotation, with no parity-based variation

### Requirement: Parity resets at the start of each batch
Parity SHALL be relative to position within the current scan batch and SHALL
reset to 1 (odd) at the start of every batch, so that a later batch of a
second book still begins with a front page.

#### Scenario: Second batch restarts with a front page
- **WHEN** a completed batch of six pages is followed by a new flatbed batch
  with the alternating-rotation toggle enabled
- **THEN** the first page of the new batch SHALL be rotated by the facing
  rotation angle

### Requirement: Rotation is applied before OCR and cleaning
With the alternating-rotation toggle enabled, each page SHALL be rotated
according to its parity before any unpaper processing or OCR is performed, so
that OCR text layers and previews are upright without re-running OCR.

#### Scenario: OCR runs on already-rotated pages
- **WHEN** a batch is scanned with the alternating-rotation toggle enabled and
  OCR is active
- **THEN** the OCR engine SHALL receive each page already rotated to its final
  upright orientation