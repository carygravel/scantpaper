# paper-size-editor

## Purpose

Enables users to define and edit custom paper sizes with sub-millimetre
precision, so the saved dimensions match what they entered at scan
resolutions where one mm spans many pixels.

## Requirements

### Requirement: Fractional paper dimensions are preserved

The paper-sizes editor SHALL preserve fractional millimetre dimensions
(with at least one digit after the decimal point) for every dimension cell
(width, height, left, top) from load through edit and save, without
truncation or rounding.

#### Scenario: Existing fractional size round-trips unchanged

- **WHEN** a paper size is defined with a fractional dimension such as
  115.2 mm in the configuration and the paper-sizes dialog is opened and
  applied
- **THEN** the saved configuration still contains 115.2 for that dimension

#### Scenario: Whole-millimetre sizes remain exact

- **WHEN** a paper size is defined with whole-millimetre dimensions
  (for example the default sizes)
- **THEN** opening and applying the paper-sizes dialog leaves those
  dimensions numerically unchanged

### Requirement: Fractional input is accepted in every dimension cell

A user editing any of the width, height, left or top cells SHALL be able to
enter a value with a decimal separator, and the entered value SHALL be
stored verbatim in the list.

#### Scenario: Typing a decimal value in a dimension cell

- **WHEN** the user types 115.2 into a dimension cell and confirms the edit
- **THEN** the cell shows and stores 115.2

#### Scenario: Invalid numeric input is rejected

- **WHEN** the user types a value that is not a number into a dimension cell
- **THEN** the edit is rejected and the previous value is kept

### Requirement: Whole-millimetre sizes display without decimals

Dimension cells SHALL display whole-millimetre values without a superfluous
trailing decimal part, so the default sizes continue to read as 210, 297
instead of 210.0, 297.0, while fractional values such as 115.2 keep their
decimal part.

#### Scenario: Default A4 size displays as whole numbers

- **WHEN** the paper-sizes dialog lists the default A4 size
- **THEN** its width and height cells display 210 and 297 without a decimal
  part

#### Scenario: Fractional size displays its decimal part

- **WHEN** the paper-sizes dialog lists a size of 115.2 by 174 mm
- **THEN** the width cell displays 115.2