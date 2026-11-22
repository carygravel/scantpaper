# test-suite-layering Specification

## Purpose

Defines how the save-PDF codec path separates fast, toolchain-independent
tests from a small real-toolchain canary and how the canary chooses its
assertions.

## Requirements

### Requirement: The save-PDF codec canary is opt-in

The codec and compression save tests SHALL be split into a fast layer that
does not run a document conversion and a real-pipeline canary that does. The
canary SHALL carry the `slow` marker and SHALL be selected explicitly; the
fast layer SHALL be selectable by deselecting that marker.

#### Scenario: The canary is selected explicitly

- **WHEN** a developer asks for the canary layer
- **THEN** the real save pipeline runs

#### Scenario: The fast layer excludes the canary

- **WHEN** the suite runs with the `slow` marker deselected
- **THEN** the codec canary is not executed
- **AND** the codec decision tests still run

### Requirement: A canary proves bilevel codec fidelity

A real-pipeline canary SHALL save a realistically sized bilevel page through
the full save pipeline and assert that the result carries a bilevel codec,
never a lossless Flate stream. This invariant SHALL hold whether or not the
installed Ghostscript rewrites bilevel images during PDF/A conversion.

#### Scenario: Bilevel page keeps a bilevel codec

- **WHEN** a bilevel page is saved to PDF
- **THEN** its image stream is CCITT Group 4 or JBIG2
- **AND** it is not a Flate stream

#### Scenario: Missing encoder falls back to Group 4

- **WHEN** a JBIG2 save is requested but no JBIG2 encoder is installed
- **THEN** the page is saved as CCITT Group 4
- **AND** the save does not fail

### Requirement: Canary assertions are selected by runtime probes

The canary SHALL choose which assertions apply from the capabilities of the
environment it runs in, such as the OCRmyPDF version, whether a JBIG2 encoder
is installed, and the Ghostscript version. It SHALL NOT rely on a hardcoded
per-distribution table.

#### Scenario: Encoder-specific assertions follow the encoder

- **WHEN** the environment has no JBIG2 encoder
- **THEN** the encoder-specific assertions are skipped
- **AND** the fallback assertions still run

#### Scenario: Version-dependent behaviour follows the installed version

- **WHEN** the installed OCRmyPDF is older or newer than the release that
  changed its lossless default
- **THEN** the assertion for that version's PDF/A request is the one that
  runs

### Requirement: Decision logic is tested independently of the environment

Codec and compression selection SHALL be covered by unit tests that pass with
any installed tool versions, by substituting the version and capability
inputs directly.

#### Scenario: Version boundary is unit-tested

- **WHEN** the version that changed the lossless default is substituted on
  either side of the boundary
- **THEN** the unit test asserts the matching request without running a
  conversion

#### Scenario: Unparseable version is conservative

- **WHEN** an unparseable version string is supplied
- **THEN** the selection takes the conservative older branch
