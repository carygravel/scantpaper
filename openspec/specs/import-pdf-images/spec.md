# import-pdf-images

## Purpose

Defines how scantpaper imports pages from a PDF by extracting its images with
`pdfimages`, including which extracted images become pages and how the
one-image-per-page expectation is enforced.

## Requirements

### Requirement: Mask images are not imported as pages
When importing a PDF page, scantpaper SHALL create one page per extracted image
whose type is `image` and SHALL NOT create pages from mask images such as soft
masks (`smask`) or stencils. When an `image` entry has an associated soft mask,
scantpaper SHALL composite the image over a white background using the mask and
import the composited result as the single page for that PDF page. Extracted
mask files SHALL be cleaned up so no leftover files remain.

#### Scenario: PDF created from a transparent image
- **WHEN** the user opens a PDF whose page contains a single image plus its soft mask
- **THEN** scantpaper imports exactly one page for that PDF page

#### Scenario: Page with an image and a soft mask
- **WHEN** `pdfimages -list` reports a page containing one `image` entry and one `smask` entry
- **THEN** scantpaper imports one page produced by compositing the `image` with its `smask` over white, and no page from the `smask` alone

### Requirement: Imported page matches the PDF rendering
When a PDF page contains an image with a soft mask, the imported page SHALL
match the appearance of the page as rendered by a PDF viewer: semi-transparent
pixels SHALL be blended with white so that anti-aliased edges are not rendered
as solid dark pixels.

#### Scenario: Semi-transparent anti-aliased edges
- **WHEN** the user imports a PDF page whose image has a soft mask with semi-transparent edge pixels
- **THEN** the imported page shows those edge pixels blended with white rather than at full image strength

### Requirement: Imported image resolution comes from its own listing entry
When importing a PDF page, scantpaper SHALL set each imported page's resolution
from the corresponding `pdfimages -list` entry rather than from the first image
listed on the page.

#### Scenario: Image and mask report different resolutions
- **WHEN** a page has an `image` entry and a `smask` entry with different resolutions
- **THEN** the imported page SHALL use the resolution of the `image` entry

### Requirement: One image per page warning counts non-mask images
The warning that scantpaper expects one image per page SHALL be raised only when
the number of non-mask images on a page differs from one, and SHALL NOT be raised
for a page that has one image plus additional mask images.

#### Scenario: Page with one image and a soft mask
- **WHEN** a page has one `image` entry and one `smask` entry
- **THEN** no one-image-per-page warning is raised

#### Scenario: Page with two real images
- **WHEN** a page has two entries of type `image` and no mask entries
- **THEN** both images are imported as pages and the one-image-per-page warning is raised
