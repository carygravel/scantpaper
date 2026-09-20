## MODIFIED Requirements

### Requirement: Typed scan-option numbers accept the locale decimal separator

A user editing a numeric scan option SHALL be able to type the value with
the locale's decimal separator and the locale's grouping (thousands)
separator. Typing any other separator character — such as an ASCII period
when the locale's decimal separator is a comma — SHALL be rejected and have
no effect on the field's text or value. The value SHALL be sent to the
backend as a canonical number (e.g. 115.2). This applies to free-text
numeric options and to ranged (spin-button) numeric options such as the
scan-area size fields.

#### Scenario: Comma is accepted for a FIXED option

- **WHEN** the user types 115,2 into a numeric scan option in a comma
  locale and activates it
- **THEN** the backend receives the canonical number 115.2

#### Scenario: A non-locale separator is rejected in a comma locale

- **WHEN** the user types 115.2 into a numeric scan option while the
  locale's decimal separator is a comma
- **THEN** the field does not accept the value and the backend does not
  receive it; the field still contains a valid numeric value

#### Scenario: The grouping separator is accepted

- **WHEN** the user types a value that uses the locale's grouping
  separator, such as 1.234 in a comma locale whose grouping separator is
  a period
- **THEN** the backend receives the canonical number 1234

## ADDED Requirements

### Requirement: Fractional scan-area values can be typed into ranged fields

A ranged (spin-button) numeric scan option SHALL accept typed values with
a fractional part using the locale's decimal separator, and SHALL preserve
sub-unit precision (e.g. 115.2 stays 115.2 and is not truncated to 115)
for the life of the widget.

#### Scenario: Fractional size typed in a comma locale

- **WHEN** the user types 115,2 into the br-y scan-area field in a comma
  locale
- **THEN** the field shows 115,2, the backend receives the canonical number
  115.2, and the value remains 115,2 when the field is re-shown

#### Scenario: Fractional size typed in a dot locale

- **WHEN** the user types 115.2 into the br-y scan-area field in a dot
  locale
- **THEN** the backend receives the canonical number 115.2

### Requirement: Fractional sizes display without trailing zeros

A ranged numeric scan option SHALL display a whole value without a decimal
part (174.0 is shown as 174) and a fractional value with the locale's
decimal separator (115.2 is shown as 115,2 in a comma locale).

#### Scenario: Whole size value displays as an integer

- **WHEN** a scan-area field has the value 174.0 in any locale
- **THEN** the field shows 174

#### Scenario: Fractional size value displays with the locale separator

- **WHEN** a scan-area field has the value 115.2 in a comma locale
- **THEN** the field shows 115,2

### Requirement: Arrow stepping of ranged size fields stays whole-unit

The step buttons of a ranged numeric scan option SHALL increase and
decrease the value by whole units only. Sub-unit values are entered by
typing, not by stepping.

#### Scenario: Arrow step moves by one whole unit

- **WHEN** a scan-area field shows 114.8 and the user clicks the up arrow
- **THEN** the field shows 115.8 (the value increases by exactly one whole
  unit, preserving the fractional part)