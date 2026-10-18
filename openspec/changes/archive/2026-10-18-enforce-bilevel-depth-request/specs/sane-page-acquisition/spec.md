## ADDED Requirements

### Requirement: Requested colour depth is honoured

When the scan options request 1-bit output - through a colour depth of
1 bit or an equivalent bilevel scan mode (such as Lineart, Binary, Black
& White, Halftone or Error Diffusion) - and the device delivers a frame
with more colour depth, scantpaper SHALL convert the frame to a 1-bit
image before importing it as a page, using the same colour-aware
threshold semantics as the threshold tool (an ink-strength cutoff with
the configured threshold value). The application SHALL inform the user
that the device did not deliver the requested depth. The notification
SHALL be non-blocking, so that a multi-page batch is not interrupted by
repeated dialogs. Frames the device delivers at the requested depth,
and frames scanned when the scan options do not request 1-bit output,
SHALL be imported unconverted.

#### Scenario: Backend delivers 8-bit despite a 1-bit request

- **WHEN** the scan options request a depth of 1 bit and the device delivers an 8-bit frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the requested depth

#### Scenario: Bilevel scan mode delivered deeper than requested

- **WHEN** the scan options request a bilevel scan mode such as Lineart and the device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the requested depth

#### Scenario: Bilevel scan mode honoured

- **WHEN** the scan options request a bilevel scan mode and the device delivers a 1-bit frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Continuous-tone scan mode leaves deeper frames untouched

- **WHEN** the scan options request a grayscale or colour scan mode and the device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Backend honours the 1-bit request

- **WHEN** the scan options request a depth of 1 bit and the device delivers a 1-bit frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: No 1-bit request leaves deeper frames untouched

- **WHEN** the scan options do not request a 1-bit depth or bilevel scan mode and the device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Colour frame despite a 1-bit request

- **WHEN** the scan options request 1-bit output and the device delivers a colour frame containing coloured content distinct from the paper
- **THEN** the converted 1-bit page SHALL render that coloured content as ink, per the colour-aware threshold semantics

#### Scenario: Notification does not block a batch

- **WHEN** several pages in one batch are delivered deeper than requested
- **THEN** each page SHALL still be imported as a 1-bit image
- **AND** the user SHALL NOT be presented with a modal dialog for each page
