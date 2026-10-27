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

### Requirement: Additional engine variables are configurable
The OCR interface SHALL provide an advanced field that accepts zero or more
additional Tesseract engine variables in `name=value` form, one per line. A
line MAY be prefixed with `-c`, which SHALL be ignored. Blank lines and lines
whose first non-whitespace character is `#` SHALL be ignored. For a non-ignored
line, the name SHALL be the text before the first `=` and the value SHALL be
the rest, trimmed. The variables SHALL be applied when the OCR engine is
initialised.

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
