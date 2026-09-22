## MODIFIED Requirements

### Requirement: Duplex rotation follows the side being scanned
In a duplex (double-sided) workflow the rotation applied to a scanned page
SHALL be chosen from the "side to scan" setting: facing pages use the facing
rotation and reverse pages use the reverse rotation. Page-number parity SHALL
NOT influence rotation in a duplex workflow or in any scan that does not have
the flatbed alternating-rotation toggle enabled. When that toggle is enabled,
parity-based alternating rotation SHALL apply as defined by the
flatbed-alternating-rotation capability.

#### Scenario: Reverse pages rotate by the reverse setting
- **WHEN** a reverse page is scanned in a double-sided workflow
- **THEN** the reverse rotation setting SHALL be applied to it regardless of
  its final page number parity

#### Scenario: Facing pages rotate by the facing setting
- **WHEN** a facing page is scanned in a double-sided workflow
- **THEN** the facing rotation setting SHALL be applied to it

#### Scenario: Parity does not influence rotation without the toggle
- **WHEN** the flatbed alternating-rotation toggle is not enabled
- **THEN** rotation SHALL be chosen solely by the side-to-scan setting and
  SHALL NOT vary with page-number parity