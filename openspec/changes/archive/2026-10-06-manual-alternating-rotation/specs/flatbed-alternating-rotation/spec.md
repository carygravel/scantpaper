## MODIFIED Requirements

### Requirement: Toggle is bound to flatbed batch scanning
The alternating-rotation toggle SHALL be available only when a flatbed is
selected as the scan source and batch scanning from the flatbed is allowed,
and either more than one page is configured for the batch or scanning is
performed one page at a time (a batch of a single page). In all other
configurations the toggle SHALL NOT be shown.

#### Scenario: Hidden outside flatbed mode
- **WHEN** the selected source is not a flatbed, or batch scanning from the
  flatbed is not allowed
- **THEN** the alternating-rotation toggle SHALL NOT be visible

#### Scenario: Visible in flatbed batch mode
- **WHEN** a flatbed is selected, batch scanning from the flatbed is allowed,
  and more than one page is configured
- **THEN** the alternating-rotation toggle SHALL be visible

#### Scenario: Visible for single-page flatbed scanning
- **WHEN** a flatbed is selected, batch scanning from the flatbed is allowed,
  and only one page is configured
- **THEN** the alternating-rotation toggle SHALL be visible

### Requirement: Parity resets at the start of each batch
For a multi-page batch, parity SHALL be relative to position within the
current scan batch and SHALL reset to 1 (odd) at the start of every batch,
so that a later batch of a second book still begins with a front page. For
single-page scans started one at a time (manual scanning), parity SHALL be
stateful across consecutive scans: each scan SHALL increment the parity
counter, and the counter SHALL reset to 1 (odd) only when the user
explicitly turns the alternating-rotation toggle off.

#### Scenario: Second batch restarts with a front page
- **WHEN** a completed batch of six pages is followed by a new flatbed batch
  with the alternating-rotation toggle enabled
- **THEN** the first page of the new batch SHALL be rotated by the facing
  rotation angle

#### Scenario: Consecutive manual scans alternate
- **WHEN** the alternating-rotation toggle is enabled and three scans are
  started one page at a time on a flatbed
- **THEN** the first and third scans SHALL be rotated by the facing rotation
  angle and the second scan SHALL be rotated by that angle plus 180 degrees
  (modulo 360 degrees)

#### Scenario: Manual parity persists until the toggle is turned off
- **WHEN** the alternating-rotation toggle is turned off and then enabled
  again without scanning in between
- **THEN** the parity counter SHALL be reset so the next scan is treated as
  an odd page
