## Purpose

Defines how the threshold tool converts pages to 1-bit black-and-white images,
including how coloured content that is visually distinct from the paper is
preserved rather than being erased by the luminance conversion.

## ADDED Requirements

### Requirement: Coloured content is preserved by the threshold
When thresholding a page, scantpaper SHALL render a pixel as black when its
colour differs from the paper (white) by more than the threshold in at least
one colour channel, and SHALL render it white otherwise. A pixel SHALL NOT be
classified by its luminance alone, so colours that are visually distinct from
white but have luminance close to white are preserved.

#### Scenario: Yellow text on a white page
- **WHEN** the user thresholds a page containing yellow text on a white background
- **THEN** the yellow text is rendered black

#### Scenario: Red stamp on a white page
- **WHEN** the user thresholds a page containing a red stamp on a white background
- **THEN** the stamp is rendered black

#### Scenario: Light-coloured annotation on a white page
- **WHEN** the user thresholds a page containing a light-coloured annotation (e.g. pink or light blue) on a white background
- **THEN** the annotation is rendered black

### Requirement: Threshold value is an ink-strength cutoff
The threshold value SHALL be interpreted as the minimum ink strength required
for a pixel to be rendered black, where ink strength measures how far a pixel's
colour is from the paper colour. The default threshold value SHALL be 20.
A lower value keeps fainter marks; a higher value keeps only stronger marks.

#### Scenario: Default threshold value
- **WHEN** the user opens the threshold tool without having changed the setting
- **THEN** the threshold value is 20

#### Scenario: Faint mark below the threshold
- **WHEN** a pixel differs from the paper colour by less than the threshold
- **THEN** the pixel is rendered white

#### Scenario: Value is a percentage of the full range
- **WHEN** the user sets the threshold to 80
- **THEN** only pixels whose ink strength exceeds 80% of the full range are rendered black, and all lighter pixels are rendered white

### Requirement: Saved threshold values keep their intended cut-off
When a user has a saved threshold value from before the change, scantpaper SHALL
reinterpret it so it represents the cut-off the user originally intended on the
new ink-strength scale (mapping value `v` to `100 - v`). The previous threshold
compared the 0-100 slider value directly against 0-255 pixel values; that
behaviour is treated as a bug and SHALL NOT be reproduced.

#### Scenario: Legacy threshold value is migrated
- **WHEN** a user has a saved threshold value of 80 from before the change
- **THEN** the value is migrated to 20, so the cut-off the user originally intended (pixels darker than 80% of the range) is preserved

### Requirement: Threshold output is 1-bit black and white
The threshold tool SHALL produce a 1-bit black-and-white image with no
remaining colour or grey levels.

#### Scenario: Thresholded page is monochrome
- **WHEN** the user applies the threshold to a colour page
- **THEN** the resulting page is 1-bit and contains only black and white pixels
