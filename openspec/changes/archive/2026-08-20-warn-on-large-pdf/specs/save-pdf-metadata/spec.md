## MODIFIED Requirements

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
