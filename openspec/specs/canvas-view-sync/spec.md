# Canvas View Sync

## Purpose

Keeps the text-layer and annotation canvases showing the same region of
the page as the image view, across tab switches, resizes, and view-mode
switches, so layer editing always starts from what the user is looking
at.

## Requirements

### Requirement: Canvases align with the image view when shown

When a text-layer or annotation canvas becomes visible (first
allocation, tab switch, or view-mode switch), it SHALL display the same
region of the page as the image view currently does: its zoom and
offset SHALL match the view's within each widget's allocation. An
offset that was pushed while the canvas had no usable allocation SHALL
be recovered at the moment the canvas is shown, not lost.

#### Scenario: Canvas shown after being hidden aligns with the view

- **WHEN** the image view displays a fitted page and the user switches
  to the text-layer or annotation tab
- **THEN** the canvas SHALL show the page in the same position and at
  the same zoom as the image view does

#### Scenario: Offset pushed while the canvas is hidden is not lost

- **WHEN** the image view re-fits while a canvas is a hidden notebook
  page
- **AND** the canvas is later shown
- **THEN** the canvas SHALL show the region the view was showing after
  the re-fit, within its own allocation

#### Scenario: Window shrink does not leave the page off-screen

- **WHEN** the window shrinks while a canvas is hidden
- **AND** the canvas is then shown
- **THEN** the page SHALL be visible within the canvas (the stored
  offset SHALL be re-clamped against the live allocation)

### Requirement: Canvas interaction propagates to the image view

Panning or zooming a canvas SHALL update the image view to the same
region, as today, and the propagation SHALL NOT corrupt either widget's
offset with a clamp against a stale allocation.

#### Scenario: Panning the text canvas pans the image view

- **WHEN** the user pans the text-layer canvas in a split view
- **THEN** the image view SHALL show the matching region
