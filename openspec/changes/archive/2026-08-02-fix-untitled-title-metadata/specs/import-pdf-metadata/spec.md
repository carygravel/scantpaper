## Purpose

Defines how scantpaper reads title metadata from imported documents, treating
placeholder titles such as `Untitled` or `'Untitled'` as empty so they do not
pollute the session metadata.

## ADDED Requirements

### Requirement: Placeholder titles normalized to empty
When scantpaper imports a document whose title metadata is a placeholder, the
imported metadata SHALL use an empty string as the title. A placeholder title
is `Untitled`, or `'Untitled'` (wrapped in literal apostrophes), compared
case-insensitively and ignoring leading or trailing whitespace.

#### Scenario: Title is "Untitled"
- **WHEN** the user imports a document whose title is `Untitled`
- **THEN** the imported metadata SHALL have an empty title

#### Scenario: Title is "'Untitled'" with apostrophes
- **WHEN** the user imports a document whose title is `'Untitled'` (with literal apostrophes)
- **THEN** the imported metadata SHALL have an empty title

#### Scenario: Title is a case variation
- **WHEN** the user imports a document whose title is `untitled` or `UNTITLED`
- **THEN** the imported metadata SHALL have an empty title

### Requirement: Real titles preserved
Title normalization SHALL NOT alter legitimate titles. A title that is not a
placeholder SHALL be imported unchanged.

#### Scenario: Import a document with a real title
- **WHEN** the user imports a document whose title is `La Voz de Galicia`
- **THEN** the imported metadata SHALL keep the title `La Voz de Galicia`

## REMOVED Requirements

_None._
