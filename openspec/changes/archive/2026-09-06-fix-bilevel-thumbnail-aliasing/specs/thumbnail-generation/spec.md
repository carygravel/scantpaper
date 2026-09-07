## MODIFIED Requirements

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