# View Layout

## Purpose

Describe how the main window arranges the image, text-layer and annotation
views, and how the split divider position is initialised and persisted across
sessions so a chosen split view remains usable.

## Requirements

### Requirement: Split panes have a visible initial divider

When the window starts in a horizontal or vertical split view, the image and
text-layer panes SHALL both be allocated a usable share of the available
space, so the split is visibly present even before any image is loaded.

#### Scenario: Split view opens at a sensible position

- **WHEN** the application starts with `viewer_tools` set to `horizontal` or
  `vertical`
- **THEN** the split panes are packed with an explicit, non-collapsed divider
  position

#### Scenario: Imported image is visible without changing views

- **WHEN** an image is imported while a split view is active at startup
- **THEN** the image is shown in its pane without the user having to switch to
  another view mode

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
