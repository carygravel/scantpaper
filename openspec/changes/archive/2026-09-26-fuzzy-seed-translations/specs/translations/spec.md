## Purpose

Defines how scantpaper's translations are produced, marked, and shipped:
fuzzy-marked translations are treated as untranslated until a human
confirms them, and only non-fuzzy translations reach end users.

## ADDED Requirements

### Requirement: Fuzzy translations fall back to English
The system SHALL treat a `#, fuzzy` translation as untranslated, so users
see the English source string for that message until the fuzzy flag is
cleared.

#### Scenario: Fuzzy string is displayed to user
- **WHEN** a catalog contains a `#, fuzzy` entry for a message and the user
  runs the application in that language
- **THEN** the user sees the English source text for that message, not the
  fuzzy translation

#### Scenario: Non-fuzzy translation is displayed to user
- **WHEN** a catalog contains a non-fuzzy entry for a message and the user
  runs the application in that language
- **THEN** the user sees the translated text for that message

### Requirement: Only non-fuzzy translations ship
Release builds SHALL include only non-fuzzy translations; fuzzy entries
SHALL never be compiled into a released catalog.

#### Scenario: Release with fuzzy entries present
- **WHEN** a release is built while a catalog still contains fuzzy entries
- **THEN** the release is built successfully with those messages falling
  back to English, and the release is not blocked by the fuzzy entries

#### Scenario: Fuzzy entries never appear in released output
- **WHEN** a released catalog is inspected for a message that is fuzzy in
  the source catalog
- **THEN** the fuzzy translation is absent from the released output and the
  English fallback is used instead

### Requirement: Missing translations may be added as fuzzy
The translation workflow SHALL allow missing strings to be translated and
marked `#, fuzzy` (needing review) rather than left untranslated.

#### Scenario: Translator confirms a fuzzy string
- **WHEN** a human translator reviews a fuzzy entry and clears its fuzzy
  flag
- **THEN** the entry becomes a shipped translation for the next release

#### Scenario: Fuzzy entry remains unreviewed
- **WHEN** a fuzzy entry has not been reviewed by a translator
- **THEN** it continues to fall back to English and is excluded from
  releases

### Requirement: Translation updates flow through Rosetta
The system SHALL continue to use the Rosetta (Launchpad) workflow to
download translated catalogs and receive cleared (non-fuzzy) translations
before a release.

#### Scenario: Translated catalog downloaded from Rosetta
- **WHEN** translated `.po` files are downloaded from Rosetta before a
  release
- **THEN** the confirmed translations are included in the release and
  unreviewed fuzzy entries continue to fall back to English
