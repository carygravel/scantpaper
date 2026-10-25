# scan-option-values

## Purpose

Makes the numeric values shown against scan options follow the user's locale,
so comma-locale users see and type the values with a comma while the SANE
backend keeps receiving canonical numbers.

## Requirements

### Requirement: Numeric scan-option values display with the locale separator

The scan dialog SHALL render numeric values that belong to a scan option —
both the items of a list/combobox option (e.g. resolutions) and the default
of a free-text entry option — using the locale's decimal separator, at the
driver's full precision, so a value of 215.9 is shown as "215,9" when the
locale uses a comma and as "215.9" otherwise, and a value of
1.07818603515625 is shown unchanged apart from the separator. Integer
values SHALL keep rendering without a decimal part.

#### Scenario: Resolution list items are localized

- **WHEN** a scan option offers the resolution list [150, 300, 215.9] and
  the user's locale uses a comma as decimal separator
- **THEN** the combobox shows the items 150, 300 and 215,9

#### Scenario: Free-text numeric default is localized

- **WHEN** a free-text numeric scan option has the default 115.2 and the
  user's locale uses a comma as decimal separator
- **THEN** the entry shows 115,2

#### Scenario: Whole-number values stay without decimals

- **WHEN** a scan option value is 150
- **THEN** it is displayed as 150 in every locale

### Requirement: Typed scan-option numbers accept the locale decimal separator

A numeric scan option SHALL accept a typed value using the locale's decimal
separator and grouping (thousands) separator. Typing any other separator
character — such as an ASCII period in a comma locale — SHALL be rejected and
have no effect on the field's text or value. The value SHALL be sent to the
backend as a canonical number (e.g. 115.2). This applies to both free-text and
ranged (spin-button) numeric options, such as the scan-area size fields.

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

### Requirement: Legacy profile values with a decimal comma are imported

When applying a scan profile whose values were read from text (pre-v3
config), a numeric option value written with a decimal comma SHALL be
converted to the canonical number instead of raising a conversion error.

#### Scenario: Pre-v3 profile with a comma is applied

- **WHEN** a pre-v3 profile contains a FIXED option whose value string is
  115,2
- **THEN** the option is applied with the canonical number 115.2