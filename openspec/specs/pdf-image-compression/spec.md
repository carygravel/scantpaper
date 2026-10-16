# pdf-image-compression

## Purpose

Defines how page images are encoded when a PDF is written: the automatic
per-image codec selection, the bilevel codec preference, the JPEG quality
applied to lossy output, CCITT Group 4 and JBIG2 for bilevel pages, JPEG
2000 compression, and when an existing encoding is embedded without
re-encoding.

## Requirements

### Requirement: Automatic compression selection

When the `auto` compression option is selected (the default), scantpaper
SHALL choose an encoding for each page from its colour model: bilevel
pages SHALL be encoded according to the bilevel codec preference (CCITT
Group 4 by default; lossless JBIG2 when the preference is configured and
the encoder is available), lossless Flate for images with an alpha
channel, and JPEG for continuous-tone (8-bit grayscale, RGB or CMYK)
pages.

#### Scenario: Bilevel page with automatic compression and the default preference

- **WHEN** a PDF is saved with automatic compression for a bilevel page and the bilevel preference is its default
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: Bilevel page with automatic compression and the JBIG2 preference

- **WHEN** a PDF is saved with automatic compression for a bilevel page, the bilevel preference is `jb2` and the encoder is available
- **THEN** the page image SHALL be embedded with lossless JBIG2 encoding

#### Scenario: Continuous-tone page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a grayscale or colour page
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Transparent page with automatic compression

- **WHEN** a PDF is saved with automatic compression for an image with an alpha channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

### Requirement: JPEG 2000 compression option

When the `jp2` compression option is selected, continuous-tone pages
(8-bit grayscale, RGB or CMYK) SHALL be embedded with lossy JPEG 2000
(JPXDecode) encoding. The colour-model rules of automatic compression
SHALL still apply: bilevel pages SHALL be encoded with CCITT Group 4 and
pages with an alpha channel SHALL be encoded losslessly with Flate.
Selecting `jp2` SHALL NOT change the behaviour of the `auto` option.

#### Scenario: Continuous-tone page with JPEG 2000 compression

- **WHEN** a PDF is saved with the `jp2` compression option for a grayscale or colour page
- **THEN** the page image SHALL be embedded with lossy JPEG 2000 (JPXDecode) encoding

#### Scenario: Bilevel page with JPEG 2000 compression

- **WHEN** a PDF is saved with the `jp2` compression option for a bilevel page
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: Transparent page with JPEG 2000 compression

- **WHEN** a PDF is saved with the `jp2` compression option for an image with an alpha channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

#### Scenario: Automatic compression is unaffected

- **WHEN** a PDF is saved with the `auto` compression option
- **THEN** the page image SHALL be encoded as defined by automatic compression selection, without JPEG 2000

#### Scenario: Original image with JPEG 2000 compression

- **WHEN** a PDF is saved with the `jp2` compression option for a page imported from a JPEG file and not modified since
- **THEN** the page image SHALL be re-encoded as JPEG 2000 rather than embedded verbatim

### Requirement: JBIG2 compression option

When the `jb2` compression option is selected and the JBIG2 encoder
(`jbig2`) is available, bilevel pages SHALL be embedded with lossless
JBIG2 encoding. Continuous-tone pages SHALL still be embedded with JPEG
and pages with an alpha channel SHALL still be encoded losslessly with
Flate. When the encoder is not available the option SHALL NOT be offered,
and bilevel pages SHALL be encoded with CCITT Group 4. Selecting `jb2`
SHALL NOT change the behaviour of the `auto` option.

#### Scenario: Bilevel page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for a bilevel page and the encoder is available
- **THEN** the page image SHALL be embedded with lossless JBIG2 encoding

#### Scenario: Continuous-tone page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for a grayscale or colour page
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Transparent page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for an image with an alpha channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

#### Scenario: JBIG2 encoder unavailable

- **WHEN** the JBIG2 encoder is not installed
- **THEN** the `jb2` compression option SHALL NOT be offered, and a bilevel page SHALL fall back to CCITT Group 4

### Requirement: Bilevel codec preference for automatic compression

A user preference SHALL determine which codec automatic compression uses
for bilevel pages. The default SHALL be CCITT Group 4. When the
preference is `jb2`, bilevel pages SHALL be embedded with lossless JBIG2
if the encoder is available, and with CCITT Group 4 otherwise. The
preference SHALL NOT affect the codec chosen for continuous-tone or
alpha pages.

#### Scenario: Default preference

- **WHEN** automatic compression is used for a bilevel page and the bilevel preference is its default
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: JBIG2 preference with the encoder available

- **WHEN** automatic compression is used for a bilevel page, the bilevel preference is `jb2` and the encoder is available
- **THEN** the page image SHALL be embedded with lossless JBIG2 encoding

#### Scenario: JBIG2 preference without the encoder

- **WHEN** automatic compression is used for a bilevel page, the bilevel preference is `jb2` and the encoder is not available
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: Preference does not affect other colour models

- **WHEN** a JPEG 2000 preference is not the issue and a PDF is saved with automatic compression for a continuous-tone or alpha page
- **THEN** the page SHALL still be embedded with JPEG or Flate encoding as defined by automatic compression selection

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

### Requirement: JPEG quality applied to output

The quality configured in the save options SHALL determine the quality of
lossy images written to the PDF, for both JPEG and JPEG 2000 encoding. The
quality SHALL always be applied as a valid integer in the supported range,
so saving never fails because the configured quality is fractional or
float-typed.

#### Scenario: Lower quality produces a smaller stream

- **WHEN** the same continuous-tone page is saved as PDF twice, once with a low JPEG quality and once with a high JPEG quality
- **THEN** the low-quality PDF SHALL contain a smaller image stream than the high-quality PDF

#### Scenario: Quality controls JPEG 2000 output

- **WHEN** the same continuous-tone page is saved as PDF with the `jp2` option, once at a low quality and once at a high quality
- **THEN** the low-quality PDF SHALL contain a smaller JPEG 2000 image stream than the high-quality PDF

#### Scenario: Float-typed quality produces a valid stream

- **WHEN** a continuous-tone page is saved as PDF with a float-typed quality value, such as `75.0`, for JPEG or JBIG2 compression
- **THEN** the page image SHALL be embedded as a valid JPEG stream without raising an error

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

- **WHEN** a PDF is saved with the `png` compression option
- **THEN** the page image SHALL be embedded losslessly with Flate encoding
