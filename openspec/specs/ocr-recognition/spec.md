# ocr-recognition

## Purpose

Generate a searchable text layer for a scanned page with tesseract, feeding page pixels to the recognition engine in memory and preserving the page's stored image.

## Requirements

### Requirement: OCR feeds page pixels to the recognition engine without intermediate files
When OCR is run on a page, the page's current in-memory pixels SHALL be passed directly to the tesseract engine; the system SHALL NOT write the page image to a temporary file as OCR input and SHALL NOT read the OCR output from a file written to disk.

#### Scenario: OCR runs without temporary image files
- **WHEN** the user runs OCR on a page
- **THEN** the page's in-memory pixels are set on the tesseract API via its in-memory image setter, recognition runs, and the hOCR output is retrieved in memory
- **AND** no temporary image or hOCR file is created on disk

### Requirement: OCR result becomes the page text layer
After recognition, the hOCR output SHALL be parsed into the page's text layer, and the page SHALL be marked as OCR'd with the time the recognition completed.

#### Scenario: OCR completes successfully
- **WHEN** recognition finishes and produces hOCR output for a page
- **THEN** the hOCR output is imported into the page's text layer
- **AND** the page's OCR flag is set and its OCR time is updated to the completion time

### Requirement: OCR preserves the stored page image
Running OCR SHALL NOT create, replace, or modify any stored image; the page SHALL keep its existing image id and the stored image bytes SHALL remain unchanged.

#### Scenario: Page image unchanged by OCR
- **WHEN** OCR completes on a page
- **THEN** the page's image id is unchanged and its stored image bytes are identical to before the operation

### Requirement: OCR text layer changes are undoable
The OCR result SHALL be recorded as a document action so that undo and redo restore the text layer state before or after the operation.

#### Scenario: Undo removes the OCR text layer
- **WHEN** the user undoes an OCR action
- **THEN** the page's text layer returns to its pre-OCR state while the stored image remains unchanged

#### Scenario: Redo re-applies the OCR text layer
- **WHEN** the user redoes an OCR action after undoing it
- **THEN** the recognized text layer is restored

### Requirement: Clearing the OCR text layer is persisted and undoable
When the user clears the OCR text layer of one or more selected pages, the
clear SHALL be dispatched through the worker thread so that the removal is
written to the stored session, SHALL be recorded as an undoable document
action, and SHALL NOT modify any stored page image. The page SHALL keep its
existing image id and the stored image bytes SHALL remain unchanged.

#### Scenario: Clearing a single page's text layer
- **WHEN** the user selects a single page that has an OCR text layer and
  activates Clear OCR
- **THEN** the page's text layer is removed from the stored session
- **AND** the page's stored image id and image bytes are unchanged

#### Scenario: Undo restores a cleared text layer
- **WHEN** the user clears the OCR text layer of a page and then triggers
  undo once
- **THEN** the page's text layer returns to its pre-clear state
- **AND** the page's stored image is unchanged

#### Scenario: Redo removes the text layer again
- **WHEN** the user undoes a clear-OCR action and then triggers redo once
- **THEN** the page's text layer is removed again

#### Scenario: Clearing multiple selected pages is one undo step
- **WHEN** the user selects N pages and clears their OCR text layers in a
  single action
- **THEN** all N text layers are removed
- **AND** the action consumes exactly one undo step, not one step per page
