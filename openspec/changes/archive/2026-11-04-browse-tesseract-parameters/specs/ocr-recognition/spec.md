# Spec Delta

## ADDED Requirements

### Requirement: Available engine parameters are discoverable in the OCR interface
The OCR interface SHALL let the user view the engine parameters that the
installed Tesseract reports, from the advanced options area, without leaving
the application. Each entry SHALL show the parameter's name, default value,
and description. The list SHALL be read from the source the application uses
to validate the advanced field; the system SHALL NOT ship a bundled parameter
list. When the list cannot be read, the interface SHALL report it as
unavailable and OCR SHALL remain runnable.

#### Scenario: Opening the parameter list
- **WHEN** the user requests the available parameters from the advanced options
  area
- **THEN** the interface lists the parameters the installed Tesseract reports
- **AND** each entry shows its name, default value, and description

#### Scenario: The list follows the installed engine
- **WHEN** the installed Tesseract reports a parameter set
- **THEN** the list shows that set, with no entries added or omitted by the
  application

#### Scenario: Unreadable list
- **WHEN** the Tesseract parameter list cannot be read
- **THEN** the interface reports that the list is unavailable
- **AND** OCR can still start with the parameters already in the field

### Requirement: The parameter list can be filtered
The parameter list SHALL provide a text filter that narrows the visible
entries as the user types. Matching SHALL be case-insensitive and SHALL apply
anywhere in an entry's name or description. When no entry matches, the
interface SHALL say that nothing matches.

#### Scenario: Filtering by name
- **WHEN** the user types `dpi` in the filter
- **THEN** entries whose name contains `dpi` are shown
- **AND** entries that contain it nowhere are hidden

#### Scenario: Filtering by description
- **WHEN** the user types a word that appears only in a parameter's description
- **THEN** that parameter is shown

#### Scenario: Case-insensitive matching
- **WHEN** the user types `DPI`
- **THEN** the same entries are shown as for `dpi`

#### Scenario: No matching entry
- **WHEN** the filter text matches no entry
- **THEN** the interface says that no parameters match

### Requirement: Selecting a parameter inserts its name into the advanced field
The parameter list SHALL offer an insert action for the selected entry.
Inserting SHALL write `name=` at the cursor in the advanced field, close the
list, return focus to the field, and leave the cursor after the `=`. When the
text before the cursor does not end with a newline, the inserted entry SHALL
begin on a new line. The action SHALL NOT write a value.

#### Scenario: Inserting into an empty field
- **WHEN** the advanced field is empty and the user inserts `user_defined_dpi`
- **THEN** the field contains `user_defined_dpi=`

#### Scenario: Inserting after an entry on the same line
- **WHEN** the text before the cursor does not end with a newline and the user
  inserts an entry
- **THEN** the inserted entry begins on a new line

#### Scenario: Focus and cursor after insertion
- **WHEN** the user inserts an entry
- **THEN** the parameter list closes
- **AND** focus is in the advanced field with the cursor after the `=`

#### Scenario: No value is inserted
- **WHEN** the user inserts an entry
- **THEN** only `name=` is written, leaving the value for the user

### Requirement: Parameters owned by dedicated controls cannot be inserted
The parameters `tessedit_pageseg_mode` and `tessedit_ocr_engine_mode` SHALL
remain visible in the parameter list and SHALL be annotated with the control
that owns them. The insert action SHALL NOT write those names into the
advanced field.

#### Scenario: A managed parameter is annotated
- **WHEN** the parameter list is shown
- **THEN** the entry for `tessedit_pageseg_mode` names the page segmentation
  mode control
- **AND** the entry for `tessedit_ocr_engine_mode` names the OCR engine mode
  control

#### Scenario: A managed parameter cannot be inserted
- **WHEN** the user selects `tessedit_pageseg_mode` and requests an insertion
- **THEN** the advanced field is unchanged
- **AND** the parameter list stays open
