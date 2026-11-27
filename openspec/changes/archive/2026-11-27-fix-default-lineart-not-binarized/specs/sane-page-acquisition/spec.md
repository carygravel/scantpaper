# Spec Delta

## ADDED Requirements

### Requirement: 1-bit output is requested by effective mode or depth

scantpaper SHALL treat 1-bit output as requested when the scanner reports an
effective scan depth of 1 bit or an effective bilevel scan mode (Lineart,
Binary, Black & White, Halftone or Error Diffusion), whether the value was
chosen in the scan dialog or is the backend's own default. An effective depth
of 1 bit SHALL take precedence over a continuous-tone mode, so a backend that
reports both requests 1-bit output. An option that is missing or inactive
SHALL count as not requested.

#### Scenario: Backend-default bilevel mode requests 1-bit output

- **WHEN** the backend's default scan mode is bilevel (e.g. Lineart) and the
  user scans without changing the mode
- **THEN** 1-bit output SHALL be treated as requested

#### Scenario: Effective depth of 1 bit wins over a continuous-tone mode

- **WHEN** the effective scan depth is 1 bit and the effective scan mode is
  grayscale or colour
- **THEN** 1-bit output SHALL be treated as requested

#### Scenario: Missing or inactive options request nothing

- **WHEN** the backend exposes no depth or mode option, or the option is
  inactive
- **THEN** 1-bit output SHALL NOT be treated as requested

## MODIFIED Requirements

### Requirement: Requested colour depth is honoured

When 1-bit output is requested and the device delivers a deeper frame,
scantpaper SHALL convert it to 1-bit before importing it, using the threshold
tool's colour-aware semantics (an ink-strength cutoff at the configured
threshold). Frames delivered at the requested depth, or when 1-bit output is
not requested, SHALL be imported unconverted.

#### Scenario: Backend delivers 8-bit despite a 1-bit request

- **WHEN** the effective scan depth is 1 bit and the device delivers an 8-bit
  frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the
  colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the
  requested depth

#### Scenario: Bilevel scan mode delivered deeper than requested

- **WHEN** the effective scan mode is a bilevel mode such as Lineart and the
  device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the
  colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the
  requested depth

#### Scenario: Backend-default bilevel mode delivered deeper than requested

- **WHEN** the backend's default scan mode is bilevel (e.g. Lineart), the user
  scans without changing the mode, and the device delivers an 8-bit or colour
  frame
- **THEN** the page SHALL be imported as a 1-bit image converted with the
  colour-aware threshold
- **AND** the user SHALL be informed that the device did not deliver the
  requested depth

#### Scenario: Bilevel scan mode honoured

- **WHEN** the effective scan mode is a bilevel scan mode and the device
  delivers a 1-bit frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Continuous-tone scan mode leaves deeper frames untouched

- **WHEN** the effective scan mode is a grayscale or colour scan mode, the
  effective scan depth is not 1 bit, and the device delivers an 8-bit or
  colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Backend honours the 1-bit request

- **WHEN** the effective scan depth is 1 bit and the device delivers a 1-bit
  frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: No 1-bit request leaves deeper frames untouched

- **WHEN** the effective scan depth is not 1 bit and the effective scan mode
  is not a bilevel mode, and the device delivers an 8-bit or colour frame
- **THEN** the page SHALL be imported unconverted

#### Scenario: Colour frame despite a 1-bit request

- **WHEN** 1-bit output is requested and the device delivers a colour frame
  containing coloured content distinct from the paper
- **THEN** the converted 1-bit page SHALL render that coloured content as ink,
  per the colour-aware threshold semantics
