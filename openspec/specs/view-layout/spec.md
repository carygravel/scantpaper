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
any image is loaded. In tabbed mode the view SHALL fill the space above the
edit bar. Each nested split pane SHALL be given an explicit, non-collapsed
divider position, so a split view does not collapse either edge.

#### Scenario: Tabbed view opens with a usable image area

- **WHEN** the application starts with `viewer_tools` set to `tabbed`
- **THEN** the image area SHALL fill the vertical space above the edit bar
- **AND** it SHALL NOT be collapsed to an edge

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
- **THEN** the split divider's default position is not re-imposed on top of
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

### Requirement: Split view shows the active layer's canvas

In a split view mode the pane beside the image SHALL show the active layer's
canvas, so the layer selected for editing is also the layer on screen. Only one
layer canvas SHALL be shown beside the image at a time.

#### Scenario: The text canvas is shown for the text layer

- **WHEN** the active layer is the text layer in a split view mode
- **THEN** the text layer canvas SHALL be shown beside the image
- **AND** the annotation canvas SHALL NOT be shown

#### Scenario: The annotation canvas is shown for the annotation layer

- **WHEN** the active layer is the annotation layer in a split view mode
- **THEN** the annotation layer canvas SHALL be shown beside the image
- **AND** the text layer canvas SHALL NOT be shown

#### Scenario: Changing the active layer swaps the canvas

- **WHEN** the user switches the active layer while in a split view mode
- **THEN** the pane beside the image SHALL swap to the newly active layer's
  canvas
- **AND** the previously shown layer canvas SHALL be removed from the pane

#### Scenario: Switching out of tabbed mode detaches the active canvas

- **WHEN** the user switches from tabbed mode to a split view mode
- **THEN** the active layer's canvas SHALL be moved out of the notebook into the
  split pane
- **AND** it SHALL remain the canvas shown beside the image

### Requirement: The edit bar takes only its minimum height

The edit bar below the view SHALL be a fixed row that occupies exactly its
natural height, so the image or split view above it keeps the remaining
vertical space. The bar SHALL take effect immediately when it appears or
disappears, and SHALL NOT be user-resizable.

#### Scenario: The bar does not claim half the view at startup

- **WHEN** the window is first shown with a layer active
- **THEN** the edit bar SHALL occupy only its natural height
- **AND** the view above it SHALL keep the rest of the available height

#### Scenario: The bar appears without a window resize

- **WHEN** the user opens a layer's page or enters a split view from the Image
  page
- **THEN** the edit bar SHALL occupy its natural height immediately
- **AND** the view above SHALL shrink by that height without waiting for a
  window resize

#### Scenario: The bar returns its space when it disappears

- **WHEN** the user leaves the layer's page or split view for the Image page
- **THEN** the edit bar SHALL take no vertical space
- **AND** the view above SHALL reclaim that space without waiting for a window
  resize

#### Scenario: The bar keeps its natural height when the layout changes

- **WHEN** the window is resized or the scanner progress bar disappears
- **THEN** the edit bar SHALL keep its natural height
- **AND** the view above SHALL absorb the whole change in available height

#### Scenario: The bar cannot be resized by dragging

- **WHEN** the user drags at the boundary between the view and the edit bar
- **THEN** the edit bar's height SHALL NOT change
- **AND** the view SHALL NOT be resized by that drag
