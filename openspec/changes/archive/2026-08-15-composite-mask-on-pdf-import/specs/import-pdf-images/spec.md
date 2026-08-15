## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Imported page matches the PDF rendering
When a PDF page contains an image with a soft mask, the imported page SHALL
match the appearance of the page as rendered by a PDF viewer: semi-transparent
pixels SHALL be blended with white so that anti-aliased edges are not rendered
as solid dark pixels.

#### Scenario: Semi-transparent anti-aliased edges
- **WHEN** the user imports a PDF page whose image has a soft mask with semi-transparent edge pixels
- **THEN** the imported page shows those edge pixels blended with white rather than at full image strength
