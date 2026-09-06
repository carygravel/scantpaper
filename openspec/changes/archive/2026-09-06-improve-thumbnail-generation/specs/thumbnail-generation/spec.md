## Purpose

Governs how page thumbnails are produced from a scanned page so that the
thumbnail panel shows sharp, legible previews without slowing down bulk imports.

## ADDED Requirements

### Requirement: Thumbnails are generated with high-quality resampling
When a thumbnail is generated for a page, the application SHALL downscale the
page image using a decimation-then-resampling approach that produces a sharp
preview (rather than a single coarse box-average pass).

#### Scenario: Generating a thumbnail from a high-resolution scan
- **WHEN** a thumbnail is generated from a scanned page larger than the
  thumbnail size
- **THEN** the page image SHALL first be box-decimated to roughly twice the
  target thumbnail size and then resampled down to the exact thumbnail size with
  a high-quality filter
- **AND** the resulting thumbnail SHALL be at most the configured thumbnail size
  (100 px) in each dimension

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

### Requirement: Thumbnail generation does not block the UI
Thumbnail generation SHALL run off the main thread so that generating
thumbnails for many pages does not freeze the interface.

#### Scenario: Bulk import of many pages
- **WHEN** a large set of pages is imported and thumbnails are generated for each
- **THEN** the interface SHALL remain responsive while the thumbnails are
  generated in the background