## ADDED Requirements

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
