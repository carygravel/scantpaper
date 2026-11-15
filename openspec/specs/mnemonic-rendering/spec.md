# mnemonic-rendering Specification

## Purpose

Governs how a keyboard mnemonic supplied by a translation reaches the
screen: the marker is an accelerator, never part of the visible text or
of what assistive technology announces, in every button the application
builds.

## Requirements

### Requirement: Translated button labels honour their mnemonic marker

Every button label whose text comes from a translation SHALL interpret a
keyboard mnemonic marker as an accelerator, so the marker character does
not appear in the displayed text.

#### Scenario: A translated label with a mnemonic shows no underscore

- **WHEN** the active catalog translates a button label as `_Löschen`
- **THEN** the button displays `Löschen`, with the character following the
  marker underlined as its keyboard mnemonic

#### Scenario: A translated label without a mnemonic is unchanged

- **WHEN** the active catalog translates a button label as `Löschen`, with
  no marker
- **THEN** the button displays `Löschen` and no character is underlined

#### Scenario: Neither toolbar nor dialog buttons leak the marker

- **WHEN** one msgid is displayed by a button in a view toolbar and by a
  button in a dialog
- **THEN** both display the text without the marker

#### Scenario: A doubled marker displays a literal underscore

- **WHEN** a translation needs a literal underscore in a label and writes
  it as `__`
- **THEN** the button displays one underscore at that position and
  creates no accelerator for it

### Requirement: An accessible name derived from a label excludes the marker

A button whose accessible name is derived from its translated label SHALL
expose the visible text, so assistive technology announces the label
without the mnemonic marker.

#### Scenario: Screen reader announces the translated label

- **WHEN** a screen reader focuses a button whose catalog translation is
  `_Löschen`
- **THEN** it announces `Löschen`

#### Scenario: An untranslated label is announced unchanged

- **WHEN** a button's label carries no marker
- **THEN** its accessible name equals its displayed text
