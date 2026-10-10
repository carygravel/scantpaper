## MODIFIED Requirements

### Requirement: Selection is bounded within the displayed page
When the user navigates from one page to another while a selection rectangle
is active, the selection SHALL remain visible on the newly displayed page,
positioned within that page's image area, so it can be previewed before
applying an operation. The selection SHALL NOT be clamped away or hidden by
the thumbnail that is shown while the page image loads. Clamping the selection
to the image bounds SHALL NOT produce a negative or zero width or height: the
resulting rectangle SHALL always have positive dimensions so that it remains
valid to draw and to apply an operation such as crop.

#### Scenario: Selection survives navigating to another page
- **WHEN** the user draws a selection on a page and then selects a different
  page
- **THEN** the selection SHALL remain visible on the new page

#### Scenario: Selection is bounded within the displayed page
- **WHEN** a selection from a previous page is re-applied to a page with a
  smaller image area
- **THEN** the visible selection SHALL be clamped to the bounds of the new
  page's image, and SHALL still be drawn (not reduced to zero size)

#### Scenario: Clamp never yields a negative rectangle
- **WHEN** a selection that extends beyond the top or left edge of the image is
  clamped to the image bounds
- **THEN** the resulting width and height SHALL be non-negative, and the
  rectangle SHALL have a positive area when any selection remains

## ADDED Requirements

### Requirement: Crop rejects invalid selections
The crop operation SHALL validate the selection dimensions before applying
them. If the requested crop width or height is not positive, the crop SHALL be
rejected and reported as an error, and SHALL NOT attempt to crop the image with
invalid coordinates.

#### Scenario: Crop with zero width is rejected
- **WHEN** the user applies a crop whose selection width is zero
- **THEN** the crop SHALL be rejected with a clear error and no image change

#### Scenario: Crop with negative width is rejected
- **WHEN** the user applies a crop whose selection width or height is negative
- **THEN** the crop SHALL be rejected with a clear error and no image change
  (it SHALL NOT raise a low-level image-library error)

#### Scenario: Valid crop still succeeds
- **WHEN** the user applies a crop whose width and height are both positive
- **THEN** the crop SHALL be applied as before
