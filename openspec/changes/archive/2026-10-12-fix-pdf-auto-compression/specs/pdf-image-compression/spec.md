## Purpose

Defines how page images are encoded when a PDF is written: the automatic
per-image codec selection, the JPEG quality applied to lossy output, CCITT
Group 4 for bilevel pages, and when an existing encoding is embedded
without re-encoding.

## ADDED Requirements

### Requirement: Automatic compression selection

When the `auto` compression option is selected (the default), scantpaper
SHALL choose an encoding for each page from its colour model: lossless
CCITT Group 4 for bilevel pages, lossless Flate for images with an alpha
channel, and JPEG for continuous-tone (8-bit grayscale, RGB or CMYK) pages.

#### Scenario: Bilevel page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a bilevel page
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: Continuous-tone page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a grayscale or colour page
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Transparent page with automatic compression

- **WHEN** a PDF is saved with automatic compression for an image with an alpha channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

### Requirement: JPEG quality applied to output

The JPEG quality configured in the save options SHALL determine the
quality of JPEG images written to the PDF.

#### Scenario: Lower quality produces a smaller stream

- **WHEN** the same continuous-tone page is saved as PDF twice, once with a low JPEG quality and once with a high JPEG quality
- **THEN** the low-quality PDF SHALL contain a smaller image stream than the high-quality PDF

### Requirement: Bilevel pages encoded as Group 4

Bilevel page images SHALL be encoded with CCITT Group 4 when the selected
compression is `auto`, `g3` or `g4`, and SHALL extract as 1-bit images.

#### Scenario: Automatic compression for a bilevel page

- **WHEN** a PDF is saved with automatic compression for a bilevel page
- **THEN** the extracted page image SHALL be 1-bit and Group 4 encoded

#### Scenario: Explicit Group 4 compression

- **WHEN** a PDF is saved with the `g4` compression option
- **THEN** the extracted page image SHALL be 1-bit and Group 4 encoded

### Requirement: Original images embedded without re-encoding

When `auto` selects JPEG and the page's stored image is an unmodified
original imported image, scantpaper SHALL embed the stored image stream
verbatim without re-encoding it.

#### Scenario: Imported JPEG with automatic compression

- **WHEN** a PDF is saved with automatic compression for a page imported from a JPEG file and not modified since
- **THEN** the embedded image stream SHALL be the original JPEG bytes

#### Scenario: Scanned page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a scanned page
- **THEN** the image SHALL be encoded at the configured JPEG quality rather than embedded verbatim

### Requirement: Explicit compression options honoured

When a specific compression algorithm is selected, the page image SHALL be
encoded consistently with that algorithm.

#### Scenario: Explicit JPEG compression

- **WHEN** a PDF is saved with the `jpg` compression option
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Explicit Flate compression

- **WHEN** a PDF is saved with the `png` or `lzw` compression option
- **THEN** the page image SHALL be embedded losslessly with Flate encoding
