# Spec Delta

## Purpose

Every dialog presents its content with a consistent outer inset and even
spacing between and within the rows it shows, so controls never touch the
window edge and adjacent widgets never touch each other.

## ADDED Requirements

### Requirement: Dialog content is inset from the window edge

The content area of every dialog SHALL be inset from the dialog's edges by a
non-zero, consistent margin, so no control touches the window border.

#### Scenario: A tool dialog opens with an inset

- **WHEN** a dialog opened from the Tools menu (Threshold, Brightness /
  Contrast, Negate, Unsharp Mask, Crop, Clean up, Split, OCR, User-defined)
  is shown
- **THEN** its content area has a non-zero margin on all four sides

#### Scenario: Every dialog shares the same inset

- **WHEN** any two dialogs are shown
- **THEN** both use the same content-area margin value

### Requirement: Dialog rows are spaced apart

Blocks appended to a dialog's content area — the page-range frame and each
option row — SHALL be separated by a consistent, non-zero vertical spacing, so
rows do not touch each other or the block above them.

#### Scenario: Rows in a multi-row dialog do not touch

- **WHEN** a dialog with more than one option row (for example Brightness /
  Contrast) is shown
- **THEN** the gap between consecutive rows is a non-zero, consistent spacing

#### Scenario: The page-range frame is separated from the first row

- **WHEN** a dialog that shows a page-range frame and an option row is shown
- **THEN** the row does not touch the frame above it

### Requirement: Widgets within a dialog row are spaced apart

Widgets placed side by side in a dialog row — a label, its control, and a unit
label — SHALL be separated by a consistent, non-zero horizontal spacing, so a
label does not touch the control beside it.

#### Scenario: A label and its spin button do not touch

- **WHEN** a dialog row with a label and a spin button (for example the
  Threshold dialog's "Ink strength") is shown
- **THEN** the gap between the label and the spin button is a non-zero spacing
