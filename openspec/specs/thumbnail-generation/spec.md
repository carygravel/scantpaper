## Purpose

Governs how page thumbnails are produced from a scanned page so that the
thumbnail panel shows sharp, legible previews without slowing down bulk imports.
## Requirements
### Requirement: Thumbnails are generated with high-quality resampling
When a thumbnail is generated for a page, the application SHALL downscale the
page image using a decimation-then-resampling approach that produces a sharp,
anti-aliased preview (rather than a single coarse box-average pass). Thumbnails
of bilevel (1-bit) or palette page images SHALL be anti-aliased the same way,
so thin text strokes remain legible rather than collapsing into a two-shade
black-and-white rendering.

#### Scenario: Generating a thumbnail from a high-resolution scan
- **WHEN** a thumbnail is generated from a scanned page larger than the
  thumbnail size
- **THEN** the page image SHALL first be box-decimated to roughly twice the
  target thumbnail size and then resampled down to the exact thumbnail size with
  a high-quality filter
- **AND** the resulting thumbnail SHALL be at most the configured thumbnail size
  (100 px) in each dimension

#### Scenario: Generating a thumbnail from a bilevel page
- **WHEN** a thumbnail is generated from a page whose image is bilevel (1-bit)
  or palette-based
- **THEN** the thumbnail SHALL be rendered as an anti-aliased grayscale or
  colour preview with intermediate shades
- **AND** the thumbnail SHALL NOT collapse into only the image's two original
  tones

#### Scenario: Generating a thumbnail from a small page
- **WHEN** the page image is already at or below the thumbnail size
- **THEN** the page image SHALL be resized to fill the configured thumbnail box,
  preserving its aspect ratio

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

### Requirement: Page metadata follows the rotated pixel dimensions
After a rotation, the width, height and x/y resolution SHALL reflect the
rotated pixel dimensions and orientation so that any use of the page's
dimensions - thumbnail generation with a correct aspect ratio, aspect-correct
previews and analysis - produces an undistorted result.

#### Scenario: 270-degree rotation swaps the page dimensions
- **WHEN** a landscape page is rotated by 270 degrees
- **THEN** the stored width and height SHALL be swapped relative to the
  pre-rotation page, and the x/y resolution SHALL be swapped likewise

#### Scenario: 90-degree rotation swaps the page dimensions
- **WHEN** a landscape page is rotated by 90 degrees
- **THEN** the stored width and height SHALL be swapped relative to the
  pre-rotation page, and the x/y resolution SHALL be swapped likewise

#### Scenario: 180-degree rotation keeps the page dimensions
- **WHEN** a page is rotated by 180 degrees
- **THEN** the stored width, height and x/y resolution SHALL be unchanged

#### Scenario: Quarter-turn rotation preserves the page aspect ratio
- **WHEN** a page is rotated by 90 or 270 degrees (in either direction)
- **THEN** the application SHALL swap the page's width and height and its x/y
  resolution to match the rotated pixel dimensions
- **AND** the thumbnail regenerated for the page SHALL have the swapped aspect
  ratio rather than being stretched or compressed to the pre-rotation shape

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

### Requirement: Thumbnail generation does not block the UI
Thumbnail generation SHALL run off the main thread so that generating
thumbnails for many pages does not freeze the interface.

#### Scenario: Bulk import of many pages
- **WHEN** a large set of pages is imported and thumbnails are generated for each
- **THEN** the interface SHALL remain responsive while the thumbnails are
  generated in the background

