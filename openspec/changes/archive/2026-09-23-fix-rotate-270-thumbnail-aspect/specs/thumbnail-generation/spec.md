## MODIFIED Requirements

### Requirement: Thumbnails respect the page aspect ratio
The thumbnail SHALL preserve the page's aspect ratio, including any non-uniform
x/y resolution of the source image, so the preview is not distorted.

#### Scenario: Non-uniform resolution page
- **WHEN** a page has a different x resolution than y resolution
- **THEN** the thumbnail SHALL be sized using the same resolution-ratio
  adjustment applied to the page's dimensions
- **AND** the thumbnail SHALL fit within the configured thumbnail size box

#### Scenario: Quarter-turn rotation keeps the page aspect ratio
- **WHEN** a page is rotated by 90 or 270 degrees (in either direction)
- **THEN** the application SHALL swap the page's width and height and its x/y
  resolution to match the rotated pixel dimensions
- **AND** the thumbnail regenerated for the page SHALL have the swapped aspect
  ratio rather than being stretched or compressed to the pre-rotation shape

## ADDED Requirements

### Requirement: Rotation keeps the page aspect ratio consistent
The width, height and x/y resolution stored for a page SHALL always reflect the
rotated pixel dimensions after a rotation that changes the page orientation
(90, 270, -90 or -270 degrees), so that any use of the page's dimensions -
thumbnail generation, aspect-correct previews and analysis - produces an
undistorted result.

#### Scenario: 270-degree rotation swaps the stored dimensions
- **WHEN** a landscape page is rotated by 270 degrees
- **THEN** the stored width and height SHALL be swapped relative to the
  pre-rotation page, and the stored x/y resolution SHALL be swapped likewise

#### Scenario: 90-degree rotation swaps the stored dimensions
- **WHEN** a landscape page is rotated by 90 degrees
- **THEN** the stored width and height SHALL be swapped relative to the
  pre-rotation page, and the stored x/y resolution SHALL be swapped likewise

#### Scenario: 180-degree rotation keeps the stored dimensions
- **WHEN** a page is rotated by 180 degrees
- **THEN** the stored width, height and resolution SHALL be unchanged