# selection-across-pages

## Purpose

Keeps the selection rectangle visible and correctly placed on every page as
the user navigates, so it can be previewed before applying an operation such
as crop.

## Requirements

### Requirement: Selection persists across page changes
When the user navigates from one page to another with a selection rectangle
active, the selection SHALL remain visible on the newly displayed page,
positioned within its image area so it can be previewed before an operation
such as crop. The selection SHALL NOT be hidden by the thumbnail shown while
the page image loads. Clamping SHALL NOT produce a negative or zero width or
height: the rectangle SHALL always have positive dimensions so it remains
valid to draw and to apply.

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

### Requirement: The image selection can be cleared explicitly

The application SHALL provide a window action that clears the image selection
rectangle to no selection. The action SHALL be reachable from the View menu,
from a toolbar button next to the selection tools, and through the Escape key
while the main window has keyboard focus. A focused control that handles Escape
SHALL keep the key, so a widget with its own Escape behavior is not shadowed by
the shortcut.

#### Scenario: Clearing with the menu action

- **WHEN** an image selection rectangle is active and the user activates
  "Clear image selection" from the View menu
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

#### Scenario: Clearing with the toolbar button

- **WHEN** an image selection rectangle is active and the user activates the
  clear button next to the selection tools
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

#### Scenario: Clearing with Escape

- **WHEN** an image selection rectangle is active, the main window has focus,
  and the user presses Escape
- **THEN** the rectangle SHALL disappear
- **AND** the image view SHALL report that no selection exists

### Requirement: Clearing the selection stops cross-page persistence

After the selection is cleared, navigating to another page SHALL NOT draw or
re-apply a rectangle. The cleared state SHALL behave like the initial state
before any selection was drawn.

#### Scenario: Cleared selection stays absent on page change

- **WHEN** the user clears the selection and then navigates to another page
- **THEN** no selection rectangle SHALL be drawn on the new page

#### Scenario: Clearing when no selection exists

- **WHEN** no image selection exists and the user activates the clear action
- **THEN** the application SHALL remain in a valid state
- **AND** no rectangle SHALL be drawn and no error SHALL be reported

### Requirement: Clearing releases selection-dependent controls

Clearing the selection SHALL disable the Add controls and SHALL leave Crop
with no region to apply. The cleared state SHALL NOT be represented as a
zero-size rectangle that still counts as a selection.

#### Scenario: Add is disabled after clearing

- **WHEN** a selection is active and the user clears it
- **THEN** the Add control SHALL be insensitive

#### Scenario: Crop is not attempted after clearing

- **WHEN** the user clears the selection and then activates Crop
- **THEN** no crop SHALL be applied
- **AND** no invalid-selection error SHALL be reported

#### Scenario: Crop dialog drops the cleared rectangle

- **WHEN** the user clears the selection while the Crop dialog is open
- **THEN** the dialog SHALL no longer consider the rectangle active
- **AND** the clear action SHALL NOT raise an error

### Requirement: Clear action availability follows the selection

The clear action, its menu item, and its toolbar button SHALL be insensitive
while no image selection exists and sensitive while one does.

#### Scenario: Clear is insensitive without a selection

- **WHEN** no image selection exists
- **THEN** the "Clear image selection" menu item and toolbar button SHALL be
  insensitive

#### Scenario: Clear is sensitive with a selection

- **WHEN** an image selection rectangle is active
- **THEN** the "Clear image selection" menu item and toolbar button SHALL be
  sensitive
