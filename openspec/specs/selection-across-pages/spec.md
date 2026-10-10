# selection-across-pages

## Purpose

Keeps the selection rectangle visible and correctly placed on every page as
the user navigates, so it can be previewed before applying an operation such
as crop.

## Requirements

### Requirement: Selection persists across page changes
When the user navigates from one page to another while a selection rectangle
is active, the selection SHALL remain visible on the newly displayed page,
positioned within that page's image area, so it can be previewed before
applying an operation. The selection SHALL NOT be clamped away or hidden by
the thumbnail that is shown while the page image loads.

#### Scenario: Selection survives navigating to another page
- **WHEN** the user draws a selection on a page and then selects a different
  page
- **THEN** the selection SHALL remain visible on the new page

#### Scenario: Selection is bounded within the displayed page
- **WHEN** a selection from a previous page is re-applied to a page with a
  smaller image area
- **THEN** the visible selection SHALL be clamped to the bounds of the new
  page's image, and SHALL still be drawn (not reduced to zero size)

### Requirement: Selection is validated against the full-resolution page
The selection SHALL be re-applied and validated against the page's
full-resolution image dimensions, not against the reduced-size thumbnail
displayed transiently while the page loads.

#### Scenario: Selection re-applied after full-resolution page loads
- **WHEN** a page is displayed via its thumbnail and the full-resolution
  image then becomes available
- **THEN** the selection SHALL be clamped against the full-resolution image
  dimensions so it remains a valid, drawable rectangle

### Requirement: Selection does not persist across application launches

The image selection rectangle SHALL be transient state that lives only for the
duration of the current session. It SHALL NOT be written to the user's config
file on exit, and SHALL NOT be restored on the next application launch, so a
stale selection from a previous session is never re-applied to a freshly opened
document.

#### Scenario: Selection is not written to the config file

- **WHEN** the user draws a selection rectangle and then quits the application
- **THEN** the selection is not stored in the user's config file

#### Scenario: No selection on a fresh launch

- **WHEN** the application is started after a previous session that had an
  active selection rectangle
- **THEN** no selection rectangle is present when a document is first displayed

#### Scenario: Within-session selection still works

- **WHEN** the user draws a selection and navigates between pages in the same
  session
- **THEN** the selection SHALL remain visible across page changes, per the
  existing page-navigation requirements
