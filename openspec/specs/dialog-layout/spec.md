# dialog-layout Specification

## Purpose

Every dialog presents its content with a consistent outer inset and even
spacing between and within the rows it shows, so controls never touch the
window edge and adjacent widgets never touch each other.

## Requirements

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

### Requirement: A dialog restores its height when optional content collapses

When optional content inside a dialog expands the dialog, collapsing that
content SHALL return the dialog to the height it had immediately before the
content was expanded. The dialog SHALL keep its current width, including any
width the user set manually.

#### Scenario: Collapsing the advanced OCR options

- **WHEN** the user opens the OCR dialog, expands **Advanced Tesseract engine
  parameters**, and collapses it again
- **THEN** the dialog returns to its pre-expansion height
- **AND** its width is unchanged

#### Scenario: Restoring a manually chosen height

- **WHEN** the user resizes a dialog taller, expands optional content, and
  collapses it
- **THEN** the dialog returns to the taller height the user chose
- **AND** it does not shrink to the content's natural height

#### Scenario: Scrolled content does not resize its host dialog

- **WHEN** the user collapses the advanced OCR options in the scan dialog's
  scrolled Postprocessing page
- **THEN** the scan dialog's height is unchanged

### Requirement: The page-range frame keeps its natural height

The page-range selector SHALL NOT request vertical expansion, and its frame
SHALL remain at the natural height of its radio buttons when the containing
dialog has surplus height. Surplus height SHALL NOT be absorbed by spreading
the radio buttons apart.

#### Scenario: Page-range frame after optional content collapses

- **WHEN** a dialog containing the page-range frame returns to its
  pre-expansion height
- **THEN** the frame is at its natural height

#### Scenario: Page-range frame in a manually enlarged dialog

- **WHEN** the user enlarges a dialog containing the page-range frame
- **THEN** the frame stays at its natural height
- **AND** the radio buttons keep their normal spacing
