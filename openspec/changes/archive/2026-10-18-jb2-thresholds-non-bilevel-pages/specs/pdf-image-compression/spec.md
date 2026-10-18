## MODIFIED Requirements

### Requirement: JBIG2 compression option

When the `jb2` compression option is selected and the JBIG2 encoder
(`jbig2`) is available, pages SHALL be embedded with lossless JBIG2
encoding: bilevel pages directly, and continuous-tone pages after
thresholding them to bilevel using the same conversion as the explicit
`g4` option. The resulting bilevel Group 4 streams SHALL then be
upgraded to JBIG2 by the same post-processing pass used by automatic
compression with the JBIG2 bilevel preference. Pages with an alpha
channel SHALL still be encoded losslessly with Flate. When the encoder
is not available the option SHALL NOT be offered, and pages SHALL be
encoded as for explicit Group 4 compression. Selecting `jb2` SHALL NOT
change the behaviour of the `auto` option.

#### Scenario: Bilevel page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for a bilevel page and the encoder is available
- **THEN** the page image SHALL be embedded with lossless JBIG2 encoding

#### Scenario: Continuous-tone page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for a grayscale or colour page and the encoder is available
- **THEN** the page image SHALL be thresholded to bilevel and embedded with lossless JBIG2 encoding

#### Scenario: Thresholding matches explicit Group 4

- **WHEN** the same grayscale or colour page is saved once with the `jb2` compression option and once with the `g4` compression option
- **THEN** both saved pages SHALL extract as 1-bit images produced by the same bilevel conversion

#### Scenario: Transparent page with JBIG2 compression

- **WHEN** a PDF is saved with the `jb2` compression option for an image with an alpha channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

#### Scenario: JBIG2 encoder unavailable

- **WHEN** the JBIG2 encoder is not installed
- **THEN** the `jb2` compression option SHALL NOT be offered, and pages SHALL be encoded as for explicit Group 4 compression when a stored `jb2` preference is loaded

#### Scenario: Automatic compression is unaffected

- **WHEN** a PDF is saved with the `auto` compression option
- **THEN** the page image SHALL be encoded as defined by automatic compression selection, without thresholding continuous-tone pages or applying JBIG2 encoding

#### Scenario: Quality does not affect JBIG2 output

- **WHEN** the same page is saved with the `jb2` compression option at two different quality settings
- **THEN** the embedded page images SHALL be identical

### Requirement: JPEG quality applied to output

The quality configured in the save options SHALL determine the quality of
lossy images written to the PDF, for both JPEG and JPEG 2000 encoding. The
quality SHALL always be applied as a valid integer in the supported range,
so saving never fails because the configured quality is fractional or
float-typed. The quality SHALL NOT affect lossless encodings.

#### Scenario: Lower quality produces a smaller stream

- **WHEN** the same continuous-tone page is saved as PDF twice, once with a low JPEG quality and once with a high JPEG quality
- **THEN** the low-quality PDF SHALL contain a smaller image stream than the high-quality PDF

#### Scenario: Quality controls JPEG 2000 output

- **WHEN** the same continuous-tone page is saved as PDF with the `jp2` option, once at a low quality and once at a high quality
- **THEN** the low-quality PDF SHALL contain a smaller JPEG 2000 image stream than the high-quality PDF

#### Scenario: Float-typed quality produces a valid stream

- **WHEN** a continuous-tone page is saved as PDF with a float-typed quality value, such as `75.0`, for JPEG or JPEG 2000 compression
- **THEN** the page image SHALL be embedded as a valid lossy stream without raising an error

#### Scenario: Quality does not affect lossless output

- **WHEN** the same page is saved with a lossless encoding option, such as `g4` or `jb2`, at two different quality settings
- **THEN** the embedded page images SHALL be identical
