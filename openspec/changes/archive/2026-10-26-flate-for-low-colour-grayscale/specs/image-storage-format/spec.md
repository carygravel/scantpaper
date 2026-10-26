# Spec Delta

## MODIFIED Requirements

### Requirement: Compact storage for continuous-tone images

When a page with a continuous-tone image (e.g. 8-bit grayscale or colour)
is imported, its full-size image SHALL be stored in the database as a JPEG
image, except that a grayscale image carrying only a few distinct
intensity levels SHALL be stored losslessly (PNG), so the level structure
is preserved.

#### Scenario: Grayscale TIFF imported

- **WHEN** an 8-bit continuous-tone grayscale TIFF page is imported
- **THEN** the stored full-size image blob SHALL be a JPEG
- **AND** the stored image SHALL reproduce the source at a quality
  equivalent to JPEG quality ~92 or better

#### Scenario: Colour image imported

- **WHEN** an opaque colour (RGB/CMYK) page is imported
- **THEN** the stored full-size image blob SHALL be a JPEG

#### Scenario: Colour image with transparency imported

- **WHEN** a colour page with an alpha channel (RGBA/LA/PA) is imported
- **THEN** the stored full-size image blob SHALL be lossless (PNG)
- **AND** transparency SHALL be preserved

#### Scenario: Low-colour-depth grayscale image imported

- **WHEN** an 8-bit grayscale image whose pixels contain only a few distinct
  intensity levels is imported
- **THEN** the stored full-size image blob SHALL be lossless (PNG)
- **AND** the distinct intensity levels SHALL be preserved exactly
