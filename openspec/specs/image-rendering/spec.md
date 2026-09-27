## Purpose

Governs how the main image view interpolates scanned pages when displaying them
on screen, so that static pages are rendered at full quality while interactive
manipulation stays responsive.

## Requirements

### Requirement: Static rendering uses high-quality interpolation
When the page is not being actively manipulated, the image view SHALL render
the page using the user-configured interpolation filter (default
`cairo.FILTER_GOOD`), regardless of the current zoom level.

#### Scenario: Full-page view at fit zoom is high quality
- **WHEN** an A4 page is displayed with "Zoom to fit" (zoom below 0.5) and the
  user is not interacting
- **THEN** the page SHALL be rendered with `cairo.FILTER_GOOD` (or the user's
  configured interpolation), not point sampling

#### Scenario: Zoomed-in static view uses configured filter
- **WHEN** a page is zoomed above 1.0 and static
- **THEN** the page SHALL be rendered with the user's configured interpolation
  filter

### Requirement: Interactive manipulation uses fast filtering
While the user is actively manipulating the view (panning/dragging or
scroll-zooming), the image view SHALL render with a fast filter
(`cairo.FILTER_FAST`) to keep interaction responsive.

#### Scenario: Dragging during a pan
- **WHEN** the user drags to pan the image
- **THEN** the image SHALL be rendered with `cairo.FILTER_FAST` for the
  duration of the drag

#### Scenario: Scroll-zooming under the pointer
- **WHEN** the user scrolls to zoom
- **THEN** the image SHALL be rendered with `cairo.FILTER_FAST` while the
  zoom is changing

### Requirement: Rendering returns to high quality on idle
When interaction ends, the image view SHALL resume high-quality rendering
without further user action.

#### Scenario: Idle after a drag
- **WHEN** the user finishes dragging and the pointer is idle
- **THEN** the image SHALL be re-rendered with the high-quality interpolation
  filter

#### Scenario: Idle after scroll-zoom
- **WHEN** scroll-zooming stops and no further input occurs
- **THEN** the image SHALL be re-rendered with the high-quality interpolation
  filter

### Requirement: Selection clamping uses the full-resolution image
When re-applying a selection during a page change, the image view SHALL clamp
the selection against the page's full-resolution image dimensions rather than
the transient thumbnail pixbuf currently being displayed. Clamping a selection
against a reduced-size thumbnail that produces a zero or negative width or
height SHALL NOT occur, so a valid selection always remains drawable.

#### Scenario: Full-resolution selection not clamped to thumbnail size
- **WHEN** a selection is made on a full-resolution page and the page is
  switched, with a thumbnail displayed during the transition
- **THEN** the selection SHALL be clamped to the full-resolution image
  dimensions, not degraded to a zero/negative size by the thumbnail
