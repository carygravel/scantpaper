# Spec Delta

## ADDED Requirements

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
