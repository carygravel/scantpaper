# Spec Delta

## MODIFIED Requirements

### Requirement: Lossless page images survive PDF/A conversion

When a page image is written to the PDF with a lossless codec, the final
saved PDF SHALL still contain that lossless image stream; the OCRmyPDF
PDF/A conversion SHALL NOT transcode it to a lossy codec. scantpaper
SHALL request lossless PDF/A image handling explicitly rather than rely
on the OCRmyPDF default, whose meaning changed across versions.

When the PDF/A converter nevertheless rewrites a bilevel page image with a
different lossless codec, scantpaper SHALL restore CCITT Group 4 encoding
before the save completes. This SHALL cover page image XObjects and images
the converter inlined into the page content, SHALL decode to the same bitmap,
and SHALL leave an image that is already CCITT Group 4 or JBIG2 unchanged.

A save whose page images are all JPEG SHALL keep them as JPEG, so the request
does not inflate an already-lossy document.

#### Scenario: Lossless Flate page preserved through save

- **WHEN** a PDF is saved with the Flate (`png`) compression option for a
  grayscale or colour page
- **THEN** the final PDF's page image SHALL be Flate-encoded
- **AND** it SHALL NOT be a JPEG

#### Scenario: Bilevel Group 4 page preserved through save

- **WHEN** a PDF is saved with the `g4` compression option
- **THEN** the final PDF's extracted page image SHALL be 1-bit and Group 4
  encoded

#### Scenario: Bilevel Group 4 page rewritten by the PDF/A converter

- **WHEN** a PDF is saved for a bilevel page selected for Group 4
- **AND** the installed PDF/A converter rewrites that image with another
  lossless codec
- **THEN** the final PDF's extracted page image SHALL be 1-bit and CCITT
  Group 4 encoded
- **AND** it SHALL decode to the bitmap written before the conversion

#### Scenario: Converted inline bilevel image restored

- **WHEN** the PDF/A converter inlines a bilevel page image into the page
  content stream and encodes it with another lossless codec
- **THEN** the final PDF's extracted page image SHALL be 1-bit and CCITT
  Group 4 encoded

#### Scenario: Already bilevel-compressed image left unchanged

- **WHEN** the PDF/A conversion leaves a page image in CCITT Group 4 or
  JBIG2
- **THEN** scantpaper SHALL NOT re-encode that image

#### Scenario: JPEG-only save remains JPEG

- **WHEN** a PDF is saved with the `jpg` compression option and every page
  image is JPEG
- **THEN** the final PDF's page image SHALL be JPEG-encoded
- **AND** it SHALL NOT be re-encoded to a lossless codec

#### Scenario: Lossless save independent of OCRmyPDF version

- **WHEN** a PDF is saved with a lossless compression option on any
  supported OCRmyPDF version
- **THEN** the final PDF's page image SHALL be lossless in every case
