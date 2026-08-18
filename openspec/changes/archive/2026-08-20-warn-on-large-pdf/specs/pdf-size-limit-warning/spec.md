## Purpose

Prevents the save pipeline from producing a PDF that exceeds 2 GiB, since
downstream tools (img2pdf linearization, Ghostscript PDF/A conversion,
pikepdf xref-stream linearization) overflow 32-bit file offsets at that
threshold and silently produce corrupt output.

## ADDED Requirements

### Requirement: Estimate output size before conversion
Before writing any pages to disk, the save operation SHALL estimate the
total output PDF size from the source images' dimensions and pixel format.

#### Scenario: Size estimated from image metadata
- **WHEN** the user initiates a PDF save
- **THEN** the system SHALL compute a per-page size estimate using image
  width, height, and pixel format before converting any images

### Requirement: Reject saves exceeding 2 GiB
When the estimated output PDF size equals or exceeds 2 GiB, the save
operation SHALL NOT proceed with conversion or PDF writing.  Instead it
SHALL report an error to the user indicating the estimated size and
suggesting that fewer pages be saved at a time.

#### Scenario: Save aborted for large estimate
- **WHEN** the estimated output PDF size is 2 GiB or larger
- **THEN** the save operation SHALL be aborted
- **AND** the user SHALL see an error message stating the estimated size
  in GiB and suggesting fewer pages

#### Scenario: Save proceeds for small estimate
- **WHEN** the estimated output PDF size is less than 2 GiB
- **THEN** the save operation SHALL proceed normally through conversion,
  text-layer embedding, and post-processing

### Requirement: Clean up temporary files on rejection
When the save is rejected because the estimated size exceeds 2 GiB, all
temporary image files written during estimation SHALL be removed before
the error is reported.

#### Scenario: Temporaries removed after rejection
- **WHEN** the save is aborted due to size estimate
- **THEN** no temporary image files SHALL remain in the session directory
