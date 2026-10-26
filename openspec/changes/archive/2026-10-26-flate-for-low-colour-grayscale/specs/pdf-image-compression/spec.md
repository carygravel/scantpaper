# Spec Delta

## MODIFIED Requirements

### Requirement: Automatic compression selection

When the `auto` compression option is selected (the default), scantpaper
SHALL choose an encoding per page from its colour model: bilevel pages per
the bilevel codec preference (CCITT Group 4 by default; lossless JBIG2
when configured and available), lossless Flate for images with an alpha
channel and for continuous-tone grayscale pages carrying only a few
distinct intensity levels, and JPEG for every other continuous-tone
(8-bit grayscale, RGB or CMYK) page.

#### Scenario: Bilevel page with automatic compression and default preference

- **WHEN** a PDF is saved with automatic compression for a bilevel page and the
  bilevel preference is its default
- **THEN** the page image SHALL be embedded with CCITT Group 4 encoding

#### Scenario: Bilevel page with automatic compression and the JBIG2 preference

- **WHEN** a PDF is saved with automatic compression for a bilevel page, the
  bilevel preference is `jb2` and the encoder is available
- **THEN** the page image SHALL be embedded with lossless JBIG2 encoding

#### Scenario: Continuous-tone page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a genuinely
  continuous-tone grayscale or colour page
- **THEN** the page image SHALL be embedded with JPEG encoding

#### Scenario: Low-colour-depth grayscale page with automatic compression

- **WHEN** a PDF is saved with automatic compression for a grayscale page whose
  pixels contain only a few distinct intensity levels
- **THEN** the page image SHALL be embedded losslessly with Flate encoding

#### Scenario: Transparent page with automatic compression

- **WHEN** a PDF is saved with automatic compression for an image with an alpha
  channel
- **THEN** the page image SHALL be embedded losslessly with Flate encoding
