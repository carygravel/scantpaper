## MODIFIED Requirements

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

#### Scenario: Dimension values are visibly rendered

- **WHEN** the paper-sizes dialog is opened with any defined paper sizes
- **THEN** every width, height, left and top cell is painted with its
  numeric value
- **AND** no dimension cell is left empty or blank