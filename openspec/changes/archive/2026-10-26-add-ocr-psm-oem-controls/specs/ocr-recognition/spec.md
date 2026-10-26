# Spec Delta

## ADDED Requirements

### Requirement: OCR supports a page segmentation mode selection
The OCR interface SHALL let the user choose a Tesseract page segmentation mode,
defaulting to the automatic mode. The chosen mode SHALL be applied to the
engine when OCR runs, and SHALL be stored in the user configuration and
restored on the next start. A stored value the application does not recognise
SHALL fall back to the automatic mode.

#### Scenario: Default segmentation mode
- **WHEN** no page segmentation mode has been stored
- **THEN** the OCR interface selects the automatic mode and OCR runs with it

#### Scenario: Choosing a mode
- **WHEN** the user selects the single-line mode and starts OCR
- **THEN** the engine is initialised for a single line of text

#### Scenario: The mode is restored
- **WHEN** the user selects a page segmentation mode, quits, and starts the
  application again
- **THEN** the OCR interface shows the selected mode

#### Scenario: Unrecognised stored mode
- **WHEN** the stored page segmentation mode is not one the application offers
- **THEN** the OCR interface falls back to the automatic mode

### Requirement: OCR supports an engine mode selection
The OCR interface SHALL let the user choose an OCR engine mode (default, LSTM
only, legacy, or combined), defaulting to the engine's default. The chosen mode
SHALL be applied when the engine is initialised for a page, and SHALL be stored
and restored. If the installed language data cannot provide the chosen mode,
OCR SHALL NOT start and the error SHALL name the engine mode.

#### Scenario: Default engine mode
- **WHEN** no engine mode has been stored
- **THEN** the engine is initialised with its default mode

#### Scenario: Choosing an engine mode
- **WHEN** the user selects LSTM only and starts OCR
- **THEN** the engine is initialised in LSTM-only mode

#### Scenario: Unavailable engine mode
- **WHEN** the user selects the legacy engine mode and the installed language
  data has no legacy engine
- **THEN** OCR does not start and the error names the engine mode
- **AND** the selected pages keep their existing text layers and stored images

#### Scenario: The mode is restored
- **WHEN** the user selects an engine mode, quits, and starts the application
  again
- **THEN** the OCR interface shows the selected mode

## MODIFIED Requirements

### Requirement: Malformed or unknown engine variables are rejected
If the advanced field contains a non-ignored line without an `=`, or names a
variable that the OCR engine does not recognise, OCR SHALL NOT start and the
user SHALL be shown an error identifying the offending entry. No page's text
layer or stored image SHALL be modified by the rejected operation. The field
SHALL also reject the engine variables owned by dedicated controls
(`tessedit_pageseg_mode` and `tessedit_ocr_engine_mode`), and the error SHALL
name the matching control.

#### Scenario: Line without an equals sign
- **WHEN** the advanced field contains `user_words_file`
- **THEN** OCR does not start and the error identifies that line

#### Scenario: Unknown variable name
- **WHEN** the advanced field contains a well-formed entry whose name the OCR
  engine does not recognise
- **THEN** OCR does not start and the error names that variable

#### Scenario: Rejected options leave pages unchanged
- **WHEN** OCR is rejected because of an invalid engine variable
- **THEN** the selected pages keep their existing text layers and stored images

#### Scenario: Page segmentation variable rejected
- **WHEN** the advanced field contains `tessedit_pageseg_mode=6`
- **THEN** OCR does not start and the error directs the user to the page
  segmentation mode control

#### Scenario: Engine mode variable rejected
- **WHEN** the advanced field contains `tessedit_ocr_engine_mode=1`
- **THEN** OCR does not start and the error directs the user to the engine mode
  control
