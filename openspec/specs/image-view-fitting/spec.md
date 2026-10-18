# Image View Fitting

## Purpose

Keeps the page visibly fitted in the image view whenever the widget's
allocation changes, so scan/import results are displayed without user
intervention and no display state can crash rendering.

## Requirements

### Requirement: Zoom-to-fit recomputes on allocation change

While zoom-to-fit is active, the image view SHALL recompute its fit zoom
and offset whenever its allocation changes, including the first
allocation after startup, window resizes, divider drags, and view-mode
switches. A pixbuf set while the widget had no usable allocation SHALL
be fitted on the first subsequent allocation without further user
action.

#### Scenario: Page set before the first allocation is fitted later

- **WHEN** a page pixbuf is set with zoom-to-fit while the widget has no
  usable allocation
- **AND** the widget then receives its first real allocation
- **THEN** the fit zoom and offset SHALL be recomputed so the page is
  visible within the new allocation

#### Scenario: Window resize re-fits the page

- **WHEN** the window is resized while zoom-to-fit is active and a page
  is displayed
- **THEN** the page SHALL be re-fitted to the new allocation

### Requirement: Display never crashes on a missing offset

The image view SHALL NOT raise an error while rendering a displayed
pixbuf when no offset has been set; the background SHALL be rendered
until a valid offset exists.

#### Scenario: Pixbuf displayed without an offset

- **WHEN** a pixbuf is set on the view and no offset has been computed
- **THEN** a draw cycle SHALL complete without raising, showing the
  background rather than crashing
