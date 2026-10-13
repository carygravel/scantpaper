## ADDED Requirements

### Requirement: Selectable PDF compression options

The PDF compression choices offered when saving SHALL be Automatic, G4,
Flate, JPEG, JPEG 2000 and None, plus JBIG2 when its encoder is available.
G3 and LZW SHALL NOT be offered, because the G4 and Flate options already
produce those streams.

#### Scenario: G3 and LZW are not offered

- **WHEN** the PDF compression choices are presented when saving
- **THEN** they SHALL NOT include G3 or LZW

#### Scenario: G4 and Flate are offered

- **WHEN** the PDF compression choices are presented when saving
- **THEN** they SHALL include G4 and Flate

#### Scenario: A stored G3 or LZW preference migrates

- **WHEN** the configuration stored a `pdf compression` of `g3` or `lzw` and it is loaded
- **THEN** the value SHALL become `g4` or `png` respectively, so the same Group 4 or Flate output is produced and the menu shows a valid selection

## MODIFIED Requirements

### Requirement: Bilevel pages encoded as Group 4

Bilevel page images SHALL be encoded with CCITT Group 4 when the `g4`
compression is selected, or when automatic compression resolves them to
Group 4 (the default bilevel preference), and SHALL extract as 1-bit
images. When automatic compression resolves a bilevel page to JBIG2, the
page SHALL extract as a lossless JBIG2 image.

#### Scenario: Automatic compression resolving to Group 4

- **WHEN** a PDF is saved with automatic compression for a bilevel page and the bilevel preference is its default
- **THEN** the extracted page image SHALL be 1-bit and Group 4 encoded

#### Scenario: Explicit Group 4 compression

- **WHEN** a PDF is saved with the `g4` compression option
- **THEN** the extracted page image SHALL be 1-bit and Group 4 encoded

### Requirement: Explicit compression options honoured

When a specific compression algorithm is selected, the page image SHALL be
encoded consistently with that algorithm.

#### Scenario: Explicit JPEG compression

- **WHEN** a PDF is saved with the `jpg` compression option
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Explicit Flate compression

- **WHEN** a PDF is saved with the `png` compression option
- **THEN** the page image SHALL be embedded losslessly with Flate encoding
