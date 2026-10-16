## MODIFIED Requirements

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
