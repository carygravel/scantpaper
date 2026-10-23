## ADDED Requirements

### Requirement: OCR supports an ordered set of languages

The OCR interface SHALL allow the user to choose one primary recognition
language and zero or more additional recognition languages. The chosen
languages SHALL be passed to the OCR engine as a single `+`-joined language
specification, with the primary language first and the additional languages in
the order the user selected them. A stored single-language specification SHALL
continue to be accepted without requiring the user to reopen the OCR selector.

#### Scenario: Adding a second language

- **WHEN** the user selects German as the primary language and adds English
- **THEN** the OCR engine receives the language specification `deu+eng`

#### Scenario: Preserving the order of several languages

- **WHEN** the user selects German as the primary language and adds English
  and then French
- **THEN** the OCR engine receives the language specification `deu+eng+fra`

#### Scenario: Existing single-language setting still works

- **WHEN** the stored OCR language setting is `eng` and the user starts OCR
  without changing the language selection
- **THEN** the OCR engine receives `eng`

#### Scenario: Removing an additional language

- **WHEN** the user removes English from a `deu+eng` selection
- **THEN** the OCR engine receives `deu`

#### Scenario: A language is selected at most once

- **WHEN** the user tries to add the primary language as an additional
  language, or adds the same additional language twice
- **THEN** the language appears only once in the language specification

### Requirement: OCR options persist across runs

The selected languages and any additional engine variables SHALL be stored in
the user configuration and restored on the next start. A configuration that
predates the additional engine variables SHALL continue to load and SHALL use
no additional variables.

#### Scenario: Multi-language selection is restored

- **WHEN** the user selects `deu+eng`, quits, and starts the application again
- **THEN** the OCR interface shows German as the primary language and English
  as an additional language

#### Scenario: Additional variables are restored

- **WHEN** the user sets `user_words_file=/home/me/words.txt`, quits, and
  starts the application again
- **THEN** the advanced OCR options field still contains that entry

#### Scenario: Configuration without the new setting

- **WHEN** the configuration file has no additional engine variables setting
- **THEN** the application starts normally and OCR uses no additional variables

### Requirement: Additional engine variables are configurable

The OCR interface SHALL provide an advanced field that accepts zero or more
additional Tesseract engine variables in `name=value` form, one per line.
Blank lines and lines whose first non-whitespace character is `#` SHALL be
ignored. For a non-ignored line, the name SHALL be the text before the first
`=` and the value SHALL be the remaining text with surrounding whitespace
removed. The variables SHALL be applied when the OCR engine is initialised for
a page.

#### Scenario: Applying a user word list

- **WHEN** the advanced field contains
  `user_words_file=/home/me/words.txt`
- **THEN** the OCR engine applies that word list during recognition

#### Scenario: Applying several variables

- **WHEN** the advanced field contains two valid entries on separate lines
- **THEN** both variables are applied during recognition

#### Scenario: Empty advanced field

- **WHEN** the advanced field is empty
- **THEN** OCR runs without any additional variables

#### Scenario: Ignoring blank lines and comments

- **WHEN** the advanced field contains blank lines and lines beginning with
  `#` between valid entries
- **THEN** only the valid entries are applied

#### Scenario: Value containing an equals sign

- **WHEN** the advanced field contains `some_variable=a=b`
- **THEN** the variable name is `some_variable` and its value is `a=b`

### Requirement: Malformed or unknown engine variables are rejected

If the advanced field contains a non-ignored line without an `=`, or names a
variable that the OCR engine does not recognise, OCR SHALL NOT start and the
user SHALL be shown an error identifying the offending entry. No page's text
layer or stored image SHALL be modified by the rejected operation.

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

### Requirement: Unavailable languages are reported without substitution

If one or more configured languages are not installed, the system SHALL
identify the unavailable language codes to the user and SHALL NOT replace them
with a different installed language. OCR SHALL NOT start until the language
selection no longer contains an unavailable language.

#### Scenario: A stored language is no longer installed

- **WHEN** the stored OCR language specification is `deu+eng` and the German
  language data is not installed
- **THEN** the OCR interface indicates that `deu` is unavailable
- **AND** starting OCR reports `deu` as unavailable
- **AND** the stored language specification is not silently replaced

#### Scenario: Correcting the selection allows OCR

- **WHEN** the user replaces or removes the unavailable language so that every
  selected language is installed
- **THEN** OCR starts normally
