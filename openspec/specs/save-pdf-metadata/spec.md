# save-pdf-metadata

## Purpose

Defines the title metadata written into PDFs saved by scantpaper: the output
matches what the user provided, and never contains a placeholder title when no
title was given.

## Requirements

### Requirement: No placeholder title in saved PDFs
When scantpaper saves a PDF and no title was provided by the user, the output
file SHALL NOT contain a placeholder title. In particular, neither the document
info `/Title` entry nor the XMP `dc:title` value SHALL be set.

#### Scenario: Save without a title
- **WHEN** the user saves a PDF without providing a title
- **THEN** the output PDF SHALL have no `/Title` entry in its document info
- **AND** the output PDF SHALL have no `dc:title` value in its XMP metadata

#### Scenario: Save with a title
- **WHEN** the user saves a PDF and provides a title
- **THEN** the output PDF SHALL retain exactly that title in its document info
- **AND** the output PDF SHALL retain exactly that title in its XMP metadata

### Requirement: Saved PDF remains valid
Removing a placeholder title SHALL NOT corrupt the saved document: the output
SHALL remain a valid, readable PDF that preserves the PDF/A structure produced
by the save pipeline.

#### Scenario: Output opens and preserves PDF/A structure
- **WHEN** a PDF saved without a title is opened after title cleanup
- **THEN** it SHALL open without errors
- **AND** its PDF/A identification SHALL be preserved
