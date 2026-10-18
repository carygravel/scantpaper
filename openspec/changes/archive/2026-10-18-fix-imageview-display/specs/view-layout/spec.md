## MODIFIED Requirements

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
