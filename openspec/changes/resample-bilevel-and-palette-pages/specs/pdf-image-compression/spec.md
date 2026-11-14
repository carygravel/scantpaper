# Spec Delta

## ADDED Requirements

### Requirement: Downsampling resamples every colour mode

When the downsampling option is selected and its target resolution is below
the page resolution, scantpaper SHALL resample the page image to the target
resolution whatever its colour mode. A bilevel page SHALL stay bilevel.
A palette page SHALL be resampled in its true colours, keeping transparency.

#### Scenario: Downsampling a bilevel page

- **WHEN** a PDF is saved with downsampling for a bilevel page
- **THEN** the embedded page image SHALL be bilevel
- **AND** its pixel dimensions SHALL correspond to the target resolution

#### Scenario: Downsampling a palette page

- **WHEN** a PDF is saved with downsampling for a palette page
- **THEN** the resampled image SHALL use the page's true colours rather than
  palette indices
- **AND** transparency SHALL be preserved when the page has it

#### Scenario: Continuous-tone downsampling is unchanged

- **WHEN** a PDF is saved with downsampling for a grayscale or colour page
- **THEN** the image SHALL be resampled as before
