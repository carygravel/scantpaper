# Spec Delta

## MODIFIED Requirements

### Requirement: Selectable PDF compression options

The PDF compression choices offered when saving SHALL be Automatic, G4,
Flate, JPEG and JPEG 2000, plus JBIG2 when its encoder is available. None
SHALL NOT be offered, because it resolved to the same Flate codec as the
Flate choice under a label that promised no compression and no
re-encoding. G3 and LZW SHALL NOT be offered, because the G4 and Flate
options already produce those streams.

#### Scenario: G3 and LZW are not offered

- **WHEN** the PDF compression choices are presented when saving
- **THEN** they SHALL NOT include G3 or LZW

#### Scenario: G4 and Flate are offered

- **WHEN** the PDF compression choices are presented when saving
- **THEN** they SHALL include G4 and Flate

#### Scenario: A stored G3 or LZW preference migrates

- **WHEN** the configuration stored a `pdf compression` of `g3` or `lzw` and it
  is loaded
- **THEN** the value SHALL become `g4` or `png` respectively, so the same Group
  4 or Flate output is produced and the menu shows a valid selection

#### Scenario: None is not offered

- **WHEN** the PDF compression choices are presented when saving
- **THEN** they SHALL NOT include None

#### Scenario: A stored None preference migrates

- **WHEN** the configuration stored a `pdf compression` of `none` and it is
  loaded
- **THEN** the value SHALL become `png`, so the same Flate output is produced
  and the menu shows a valid, honest selection
