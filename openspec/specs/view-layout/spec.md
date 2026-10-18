# View Layout

## Purpose

Describe how the main window arranges the image, text-layer and annotation
views, and how the split divider position is initialised and persisted across
sessions so a chosen split view remains usable.

## Requirements

### Requirement: Split panes have a visible initial divider

When the window starts in any viewer mode (tabbed, horizontal, or
vertical), the image view SHALL be allocated a usable, non-collapsed
share of the available space, so the image area is usable even before
any image is loaded. This SHALL hold for the outermost pane containing
the image area as well as any nested split panes.

#### Scenario: Tabbed view opens with a usable image area

- **WHEN** the application starts with `viewer_tools` set to `tabbed`
- **THEN** the pane containing the image view is given an explicit,
  non-collapsed divider position, leaving the image area a usable share
  of the available space

#### Scenario: Split view opens at a sensible position

- **WHEN** the application starts with `viewer_tools` set to `horizontal`
  or `vertical`
- **THEN** the split panes are packed with an explicit, non-collapsed
  divider position

#### Scenario: Imported image is visible without changing views

- **WHEN** an image is scanned or imported while any viewer mode is
  active at startup
- **THEN** the image is shown in the image view without the user having
  to switch to another view mode or drag a divider

#### Scenario: Divider survives a view-mode switch

- **WHEN** the user switches between tabbed and split views after
  adjusting the divider
- **THEN** the image area's default position is not re-imposed on top of
  the user's adjustment for the remainder of the session

### Requirement: Split divider position persists across sessions

The divider position of the active split view SHALL be saved when the
application exits and restored on the next launch, so a user's chosen split
ratio is retained.

#### Scenario: Divider position restored after restart

- **WHEN** the user adjusts the split divider and quits
- **THEN** the next launch restores the same divider position for the same
  view mode

#### Scenario: Default position used when none is stored

- **WHEN** no split-pane position has been persisted
- **THEN** the split opens at a sensible default that keeps both panes visible
