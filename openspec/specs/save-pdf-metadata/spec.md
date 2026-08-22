# save-pdf-metadata

## Purpose

Defines the document metadata written into PDFs saved by scantpaper: the
output title matches what the user provided, never contains a placeholder
title when no title was given, and identifies scantpaper as the creating
application while preserving OCR toolchain provenance.

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

The save pipeline SHALL NOT attempt to produce output that would exceed 2 GiB,
since downstream tools (img2pdf linearization, Ghostscript PDF/A conversion,
pikepdf xref-stream linearization) overflow 32-bit file offsets at that size
and produce corrupt output.  When the estimated output would reach this
threshold, the save SHALL be aborted with an informative error before any
conversion begins.

#### Scenario: Output opens and preserves PDF/A structure
- **WHEN** a PDF saved without a title is opened after title cleanup
- **THEN** it SHALL open without errors
- **AND** its PDF/A identification SHALL be preserved

#### Scenario: Save rejected for oversized output
- **WHEN** the estimated output PDF size equals or exceeds 2 GiB
- **THEN** the save SHALL be aborted before conversion starts
- **AND** the user SHALL receive an error explaining the size limit and
  suggesting fewer pages

### Requirement: Saved PDFs identify scantpaper as creator
When scantpaper saves a PDF whose text layer was embedded successfully, the
output SHALL identify scantpaper as the creating application: the document
info `/Creator` entry and the XMP `xmp:CreatorTool` value SHALL begin with
`scantpaper v<version>` followed by the creator string produced by the OCR
pipeline, preserving the provenance of the underlying tools. Both values
SHALL carry the same creator string. The producer fields (`/Producer` and
`pdf:Producer`) SHALL be left as written by the save pipeline.

#### Scenario: Creator branding after saving with a text layer
- **WHEN** the user saves a PDF and at least one page has a text layer
- **THEN** the output PDF's document info `/Creator` SHALL start with
  `scantpaper v`
- **AND** it SHALL also name the OCR toolchain previously recorded by the
  pipeline (e.g. `OCRmyPDF ... / Tesseract ...`)
- **AND** the XMP `xmp:CreatorTool` value SHALL equal the `/Creator` value

#### Scenario: Creator branding with user-provided title
- **WHEN** the user saves a PDF providing a title
- **THEN** the title requirements of this capability SHALL continue to hold
- **AND** the creator branding SHALL be applied as for any other save

#### Scenario: Branding preserves PDF validity
- **WHEN** creator branding is applied to a saved PDF
- **THEN** the output SHALL remain a valid, readable PDF that preserves the
  PDF/A structure produced by the save pipeline
