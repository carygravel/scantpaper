## MODIFIED Requirements

### Requirement: Fractional input is accepted in every dimension cell

A user editing any of the width, height, left or top cells SHALL be able to
enter a fractional value using the locale's decimal separator, and SHALL also
be able to use a period, whatever the locale. The entered value SHALL be
stored as a float and shown again with the locale's decimal separator.

#### Scenario: Typing a decimal value in a dimension cell

- **WHEN** the user types 115.2 into a dimension cell and confirms the edit
- **THEN** the cell stores 115.2

#### Scenario: Typing the locale's decimal separator in a dimension cell

- **WHEN** the user's locale uses a comma as decimal separator and the user
  types 115,2 into a dimension cell and confirms the edit
- **THEN** the cell stores 115.2

#### Scenario: Period works in a decimal-comma locale

- **WHEN** the user's locale uses a comma as decimal separator and the user
  types 115.2 into a dimension cell and confirms the edit
- **THEN** the cell stores 115.2

#### Scenario: Invalid numeric input is rejected

- **WHEN** the user types a value that is not a number into a dimension cell
- **THEN** the edit is rejected and the previous value is kept

### Requirement: Whole-millimetre sizes display without decimals

Dimension cells SHALL display whole-millimetre values without a superfluous
trailing decimal part, so the default sizes continue to read as 210, 297
instead of 210.0, 297.0, while fractional values such as 115.2 keep their
decimal part rendered with the locale's decimal separator.

#### Scenario: Default A4 size displays as whole numbers

- **WHEN** the paper-sizes dialog lists the default A4 size
- **THEN** its width and height cells display 210 and 297 without a decimal
  part

#### Scenario: Fractional size displays its decimal part

- **WHEN** the paper-sizes dialog lists a size of 115.2 by 174 mm
- **THEN** the width cell displays 115.2 using the locale's decimal separator
  (e.g. 115,2 where the locale uses a comma)

#### Scenario: Dimension values are visibly rendered

- **WHEN** the paper-sizes dialog is opened with any defined paper sizes
- **THEN** every width, height, left and top cell is painted with its
  numeric value
- **AND** no dimension cell is left empty or blank