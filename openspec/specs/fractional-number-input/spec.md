# Fractional Number Input

## Purpose

Makes every user-editable fractional numeric spin field in the application
follow the locale: typed values accept the locale's decimal separator, reject
any other separator or non-numeric text, and whole values display without a
trailing decimal part.

## Requirements

### Requirement: Fractional spin fields accept the locale decimal separator

A spin button that can hold a fractional value SHALL accept a value typed
with the locale's decimal separator and SHALL preserve the sub-unit part for
the life of the widget. This covers the page Properties dialog X/Y Resolution
(DPI) fields, the Preferences Blank threshold and Dark threshold, and the
unpaper dialog White threshold and Black threshold.

#### Scenario: Fraction typed in a comma locale

- **WHEN** the user types 0,9 into the unpaper white-threshold field while
  the locale's decimal separator is a comma
- **THEN** the field holds the canonical number 0.9

#### Scenario: Fraction typed in a dot locale

- **WHEN** the user types 215.9 into the X Resolution field while the
  locale's decimal separator is a period
- **THEN** the field holds the canonical number 215.9

### Requirement: Non-locale separators and non-numeric text are rejected

When the user types a number that uses a separator other than the locale's
decimal or grouping separator, or text that is not a number, the field SHALL
reject the input: the previous valid value SHALL be restored and no invalid
value SHALL be propagated to the rest of the application.

#### Scenario: Period rejected in a comma locale

- **WHEN** the user types 215.9 into the X Resolution field while the
  locale's decimal separator is a comma and the field previously held 300
- **THEN** the field reverts to 300 and never holds 215.9

#### Scenario: Non-numeric text rejected

- **WHEN** the user types letters or other non-numeric text into a Blank
  threshold field and leaves it
- **THEN** the field reverts to the previous value

### Requirement: Fractional spin fields display without trailing zeros

A fractional spin field SHALL display a whole value without a decimal part
(300 DPI is shown as 300, a 0.9 threshold as 0,9) and a fractional value with
its decimal part rendered using the locale's decimal separator.

#### Scenario: Whole DPI displays without decimals

- **WHEN** the page Properties dialog shows a resolution of 300.0 DPI
- **THEN** the X Resolution field displays 300

#### Scenario: Fractional threshold displays with the locale separator

- **WHEN** the Preferences dialog shows a Blank threshold of 0.9 while the
  locale uses a comma as decimal separator
- **THEN** the Blank threshold field displays 0,9