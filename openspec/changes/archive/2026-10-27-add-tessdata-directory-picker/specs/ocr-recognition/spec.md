# Spec Delta

## ADDED Requirements

### Requirement: OCR supports an alternative tessdata directory
The OCR interface SHALL let the user choose or clear the directory that
contains the Tesseract language data. An empty selection SHALL keep the
engine's automatic directory. A chosen directory SHALL determine which
languages are offered and SHALL be passed to the engine when OCR starts.

#### Scenario: Default directory
- **WHEN** no tessdata directory has been selected
- **THEN** the language list is read from the automatic directory
- **AND** OCR uses that directory

#### Scenario: Choosing a directory
- **WHEN** the user selects `/models/tessdata_best` and starts OCR
- **THEN** the language list is read from `/models/tessdata_best`
- **AND** the OCR engine is initialised with `/models/tessdata_best`

#### Scenario: Language list follows the directory
- **WHEN** the user changes the tessdata directory
- **THEN** the language list is rebuilt from the new directory

#### Scenario: Current language is preserved
- **WHEN** the current OCR language is not present in the newly selected
  directory
- **THEN** the language remains selected and is shown as not installed
- **AND** it is not silently replaced with another language

#### Scenario: Returning to the default
- **WHEN** the user clears the tessdata directory
- **THEN** the language list and OCR return to the automatic directory

### Requirement: The tessdata directory is resolved with a defined precedence
The system SHALL resolve the effective tessdata directory from the explicit
selection first, then `TESSDATA_PREFIX`, then the system default. An explicit
selection SHALL win over the environment, and the system SHALL NOT fall back
to another directory when the selected source is invalid.

#### Scenario: Explicit selection wins over the environment
- **WHEN** the selected directory is `/models/tessdata_best` and
  `TESSDATA_PREFIX` names `/models/tessdata`
- **THEN** OCR uses `/models/tessdata_best`

#### Scenario: Environment is used when nothing is selected
- **WHEN** no directory is selected and `TESSDATA_PREFIX` names a valid
  tessdata directory
- **THEN** OCR uses the directory named by `TESSDATA_PREFIX`

#### Scenario: System default is used without a selection or environment
- **WHEN** no directory is selected and `TESSDATA_PREFIX` is not set
- **THEN** OCR uses the system default tessdata directory

#### Scenario: No silent fallback from an invalid explicit selection
- **WHEN** the selected directory is invalid and `TESSDATA_PREFIX` names a
  valid tessdata directory
- **THEN** OCR does not start and the error names the selected directory
- **AND** the environment directory is not used instead

### Requirement: Invalid tessdata directories are rejected before OCR starts
If the effective tessdata directory does not exist, is not a directory, cannot
be read, or directly contains no `.traineddata` file, OCR SHALL NOT start. The
user SHALL be shown an error naming the directory and the problem, and the
selected pages SHALL keep their existing text layers and stored images.

#### Scenario: Missing directory
- **WHEN** the effective tessdata directory does not exist
- **THEN** OCR does not start and the error names the missing directory

#### Scenario: Path is not a directory
- **WHEN** the effective tessdata path names a file
- **THEN** OCR does not start and the error says that the path is not a
  directory

#### Scenario: Directory cannot be read
- **WHEN** the effective tessdata directory exists but cannot be read
- **THEN** OCR does not start and the error names the unreadable directory

#### Scenario: Directory has no language data
- **WHEN** the effective tessdata directory directly contains no
  `.traineddata` file
- **THEN** OCR does not start and the error says that no language data was
  found in that directory

#### Scenario: Rejected directory leaves pages unchanged
- **WHEN** OCR is rejected because the tessdata directory is invalid
- **THEN** the selected pages keep their existing text layers and stored
  images

### Requirement: A broad TESSDATA_PREFIX is rejected before language discovery
When `TESSDATA_PREFIX` is set, the system SHALL verify that it directly
contains at least one `.traineddata` file before asking Tesseract to list
languages. A value that does not SHALL be rejected with an error naming the
expected directory, and the system SHALL NOT recurse through the parent.

#### Scenario: Broad parent is rejected
- **WHEN** `TESSDATA_PREFIX` names a broad parent such as `/usr/share`
- **THEN** the system reports that it is not a tessdata directory
- **AND** it does not ask Tesseract to list languages through that parent

#### Scenario: Parent of a tessdata directory is rejected
- **WHEN** `TESSDATA_PREFIX` names `/usr/share/tesseract-ocr/5` rather than
  `/usr/share/tesseract-ocr/5/tessdata`
- **THEN** the error identifies the directory that directly contains the
  `.traineddata` files

#### Scenario: Valid environment directory is accepted
- **WHEN** `TESSDATA_PREFIX` directly contains `.traineddata` files
- **THEN** the language list and OCR use that directory

#### Scenario: Rejected environment value leaves pages unchanged
- **WHEN** OCR is rejected because `TESSDATA_PREFIX` is not a tessdata
  directory
- **THEN** the selected pages keep their existing text layers and stored
  images

### Requirement: The tessdata directory persists across runs
The selected tessdata directory SHALL be stored in the user configuration and
restored on the next start. A configuration that predates the setting SHALL
continue to load and SHALL use the automatic directory.

#### Scenario: Selection is restored
- **WHEN** the user selects `/models/tessdata_best`, quits, and starts the
  application again
- **THEN** the OCR interface shows that directory
- **AND** the language list comes from it

#### Scenario: Configuration without the setting
- **WHEN** the configuration file has no tessdata directory setting
- **THEN** the application starts normally and OCR uses the automatic
  directory

#### Scenario: Clearing the selection persists
- **WHEN** the user clears the tessdata directory, quits, and starts the
  application again
- **THEN** the OCR interface shows the automatic directory
