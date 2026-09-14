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

A user editing a free-text numeric scan option SHALL be able to type the
value with the locale's decimal separator. The value SHALL be sent to the
backend as a canonical number (e.g. 115.2), and a period SHALL keep working.

#### Scenario: Comma is accepted for a FIXED option

- **WHEN** the user types 115,2 into a free-text numeric scan option in a
  comma locale and activates it
- **THEN** the backend receives the canonical number 115.2

#### Scenario: Period still works in a comma locale

- **WHEN** the user types 115.2 into a free-text numeric scan option in a
  comma locale and activates it
- **THEN** the backend receives the canonical number 115.2

### Requirement: Legacy profile values with a decimal comma are imported

When applying a scan profile whose values were read from text (pre-v3
config), a numeric option value written with a decimal comma SHALL be
converted to the canonical number instead of raising a conversion error.

#### Scenario: Pre-v3 profile with a comma is applied

- **WHEN** a pre-v3 profile contains a FIXED option whose value string is
  115,2
- **THEN** the option is applied with the canonical number 115.2