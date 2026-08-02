## Purpose

Metadata completion entries in the save dialog surface previously used
values while the user types, matching the typed text anywhere in a
suggestion and ranking prefix matches above substring matches.

## ADDED Requirements

### Requirement: Substring matching

An `EntryCompletion` SHALL match a suggestion when the text entered in the
entry occurs anywhere within the suggestion, rather than only at the start.
Matching SHALL be case-insensitive.

#### Scenario: Text occurs in the middle of a suggestion
- **WHEN** the entry contains "vox"
- **AND** the suggestions include "La Voz de Galicia" and "voxel"
- **THEN** both suggestions SHALL match

#### Scenario: Case-insensitive match
- **WHEN** the entry contains "br"
- **AND** the suggestions include "Brian" and "Sabrina"
- **THEN** both suggestions SHALL match

#### Scenario: No match
- **WHEN** the entry contains "xyz"
- **AND** no suggestion contains "xyz"
- **THEN** no suggestion SHALL match

### Requirement: Prefix-first ranking

When more than one suggestion matches, suggestions whose start matches the
entered text SHALL be ordered before suggestions that match only in the
middle. Exact matches SHALL rank highest. Suggestions that do not match at
all SHALL NOT appear.

#### Scenario: Prefix matches before substring matches
- **WHEN** the entry contains "br"
- **AND** the suggestions include "Brian", "Sabrina", and "breeze"
- **THEN** "Brian" and "breeze" SHALL be ordered before "Sabrina"

#### Scenario: Exact match ranks first
- **WHEN** the entry contains "Brian"
- **AND** the suggestions include "Sabrina", "Brian", and "Brianna"
- **THEN** "Brian" SHALL be the first suggestion

#### Scenario: Inline completion uses the top-ranked match
- **WHEN** the entry contains "br"
- **AND** the suggestions include "Sabrina" and "Brian"
- **THEN** the inline completion SHALL complete to a prefix match ("Brian")

### Requirement: Ranking applies to all metadata suggestion fields

The substring matching and prefix-first ranking SHALL apply to the title,
author, subject, and keywords suggestion entries in the save dialog.

#### Scenario: Author suggestions ranked
- **WHEN** the author entry contains "jo"
- **AND** the author suggestions include "John Smith" and "Dejo"
- **THEN** "John Smith" SHALL be ordered before "Dejo"

#### Scenario: Keyword suggestions ranked
- **WHEN** the keywords entry contains "scan"
- **AND** the keyword suggestions include "scanned document" and "rescan"
- **THEN** "scanned document" SHALL be ordered before "rescan"
