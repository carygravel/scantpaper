## Why

Scantpaper's OCR dialog offers exactly one Tesseract language, so users cannot
recognise a page containing more than one language (for example, `deu+eng`).
The Tesseract backend already accepts a `+`-joined language specification, and
the stored `ocr language` setting is a plain string, but the single-select
combo cannot represent it. A stored multi-language value is silently replaced
with the first installed language the next time the user scans.

Users also cannot pass other Tesseract settings, such as a user word list, even
though the engine supports them. Issue #89 asks for these options, but frames
them as command-line arguments; the application now calls tesserocr in memory,
so raw CLI flags are the wrong abstraction.

## What Changes

- Replace the single-language OCR combo with a primary-language control plus
  an additional-languages selector. The selected languages are stored, in
  order, as a `+`-joined specification in the existing `"ocr language"`
  setting (for example, `deu+eng`). Existing single-language settings and
  configuration files continue to work unchanged.
- Add an advanced "Tesseract options" field that accepts one `name=value`
  setting per line (for example, `user_words_file=/home/me/words.txt`). The
  values are passed to the engine at initialisation and persisted in a new
  `"tesseract variables"` setting. This exposes user word/pattern lists and
  other engine variables without introducing raw CLI parsing.
- Validate language codes and variable names and report unknown values to the
  user instead of silently ignoring them or replacing a missing language.
- Add a README section covering multi-language pages, user word lists, and the
  `tessdata_best` models.
- **Non-goals:** raw command-line argument parsing, first-class PSM/OEM
  controls, a custom tessdata directory, and any change to the in-memory,
  no-temporary-file OCR pipeline.

## Capabilities

### New Capabilities

<!-- None: the change extends the existing OCR behaviour. -->

### Modified Capabilities

- `ocr-recognition`: OCR accepts an ordered multi-language specification and
  additional Tesseract engine variables, reports invalid language/variable
  input, and no longer silently substitutes a different language when the
  configured one is unavailable.

## Impact

- `src/scantpaper/postprocess_controls.py`: language selector, additional
  languages, advanced options field, validation.
- `src/scantpaper/tesseract.py`: parse/join/validate language specifications
  and `name=value` variables.
- `src/scantpaper/docthread.py`: initialise tesserocr with `InitFull` so
  variables and multi-language specs are applied in one step.
- `src/scantpaper/document.py`, `src/scantpaper/tools_menu_mixins.py`,
  `src/scantpaper/scan_menu_item_mixins.py`, `src/scantpaper/config.py`:
  forward and persist the additional options.
- `src/scantpaper/tests/test_postprocess_controls.py`,
  `test_docthread.py`, `test_tool_menu_mixins.py`,
  `test_scan_menu_item_mixins.py`, `test_411_tesseract.py`: cover multi-language
  specs, variables, validation, and persistence.
- `po/scantpaper/*.po`: new UI strings marked fuzzy for translator review.
- `README.md`: user-facing documentation for the new options.
- No new dependency and no database schema change.
