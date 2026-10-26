# Spec Delta

## ADDED Requirements

### Requirement: Command-line flags are rejected with the equivalent engine parameter
The advanced options field SHALL treat a non-ignored line whose first
non-whitespace characters are `-` or `--` (other than the accepted `-c`
prefix) as a command-line option. OCR SHALL NOT start and the error SHALL
identify the option as a command-line flag. Where the application knows the
equivalent engine parameter, the error SHALL name it: `--user-words` names
`user_words_file`, `--user-patterns` names `user_patterns_file`, and `--dpi`
names `user_defined_dpi`.

#### Scenario: A flag with an equivalent parameter
- **WHEN** the advanced field contains `--user-words /home/me/words.txt`
- **THEN** OCR does not start and the error identifies `--user-words` as a
  command-line option
- **AND** the error names `user_words_file` as the engine parameter to use

#### Scenario: The `--dpi` flag
- **WHEN** the advanced field contains `--dpi 300`
- **THEN** OCR does not start and the error names `user_defined_dpi` as the
  engine parameter to use

#### Scenario: A flag without an equivalent parameter
- **WHEN** the advanced field contains `--psm 6`
- **THEN** OCR does not start and the error identifies `--psm` as a
  command-line option
- **AND** no engine parameter is suggested

#### Scenario: Rejected flags leave pages unchanged
- **WHEN** OCR is rejected because the advanced field contains a command-line
  flag
- **THEN** the selected pages keep their existing text layers and stored images

### Requirement: File-valued engine parameters are verified before OCR starts
When the advanced options name `user_words_file` or `user_patterns_file`, the
system SHALL resolve the path and verify, before OCR starts, that it names an
existing, readable file. If the verification fails, OCR SHALL NOT start and the
error SHALL identify the entry and the resolved path. The path SHALL be
resolved without expanding `~` or environment variables.

#### Scenario: Missing word list
- **WHEN** the advanced field contains `user_words_file=/home/me/words.txt`
  and that file does not exist
- **THEN** OCR does not start and the error names `user_words_file` and the
  resolved path that was not found

#### Scenario: Unreadable word list
- **WHEN** the advanced field contains `user_patterns_file=/home/me/patterns`
  for a file that exists but cannot be read
- **THEN** OCR does not start and the error names that entry

#### Scenario: Valid file starts OCR
- **WHEN** the advanced field contains `user_words_file` naming a readable file
- **THEN** OCR starts normally

#### Scenario: Tilde is not expanded
- **WHEN** the advanced field contains `user_words_file=~/words.txt`
- **THEN** the path is treated literally rather than expanded to the home
  directory
- **AND** if no such file exists the error reports the resolved path

#### Scenario: Rejected file entries leave pages unchanged
- **WHEN** OCR is rejected because a file-valued parameter cannot be read
- **THEN** the selected pages keep their existing text layers and stored images

### Requirement: Applied engine options are recorded in the log
When OCR starts, the engine parameters that will be applied, including the
resolved paths of any file-valued parameters, SHALL be recorded in the
application log.

#### Scenario: Word list recorded
- **WHEN** the user runs OCR with `user_words_file=/home/me/words.txt`
- **THEN** the log records that parameter and its resolved path

## MODIFIED Requirements

### Requirement: Additional engine variables are configurable
The OCR interface SHALL provide an advanced field that accepts zero or more
additional Tesseract engine variables in `name=value` form, one per line.
A line MAY be prefixed with `-c`, which SHALL be ignored so that an entry
pasted from tesseract's command-line documentation is accepted. Blank lines
and lines whose first non-whitespace character is `#` SHALL be ignored. For a
non-ignored line, the name SHALL be the text before the first `=` and the value
SHALL be the remaining text with surrounding whitespace removed. The variables
SHALL be applied when the OCR engine is initialised for a page.

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

#### Scenario: Pasted -c prefix
- **WHEN** the advanced field contains `-c tessedit_char_whitelist=0123456789`
- **THEN** the variable name is `tessedit_char_whitelist` and its value is
  `0123456789`
