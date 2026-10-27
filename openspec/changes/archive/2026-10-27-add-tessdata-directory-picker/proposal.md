# Proposal

## Why

Tesseract 4 and later no longer have the Tesseract 3 `m_data_sub_dir`
parameter, and the advanced OCR field correctly rejects it. Users who want
`tessdata_best`, `tessdata_fast`, or a per-user model set currently have to
replace the system models or set `TESSDATA_PREFIX` before launching the
application. The latter is unreliable for desktop launches, and a
`TESSDATA_PREFIX` that names a broad parent makes Tesseract recurse and hang
while listing languages. The advanced field cannot express the data directory
because it is an engine initialisation argument, not a `-c` variable.

## What Changes

- Add a **Tessdata directory** row to the OCR controls, with a text entry, a
  **Browse** folder chooser, and a **Default** reset. An empty value keeps
  today's automatic behaviour.
- Persist the selected directory as `"tessdata directory"`; configurations
  without the key load unchanged and use the automatic behaviour.
- Resolve the effective data directory in one place: explicit setting first,
  then `TESSDATA_PREFIX`, then the system default. Every path must directly
  contain at least one `.traineddata` file.
- Reject an invalid explicit path, an invalid default, or a broad
  `TESSDATA_PREFIX` with a clear error before OCR starts. Do not silently fall
  back to another directory.
- Rebuild the language list when the directory changes. A language that the
  new directory lacks is kept in the selection and marked as not installed,
  matching the existing missing-language behaviour.
- Pass the effective directory to the OCR worker and use it for engine
  initialisation; the worker re-validates it.
- Document the picker, precedence, validation, and the fact that
  `m_data_sub_dir` is obsolete. Do not reintroduce it as an engine variable.

No breaking changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ocr-recognition`: add an alternative tessdata directory selection with
  defined resolution precedence, validation, a guard against a broad
  `TESSDATA_PREFIX`, and persistence of the selection.

## Impact

- `src/scantpaper/postprocess_controls.py`: the OCR row, language reload, and
  validation.
- `src/scantpaper/tesseract.py`: shared tessdata directory resolution and
  validation; the `_find_tessdata_path` fallback moves here.
- `src/scantpaper/docthread.py`: use the resolved path and re-validate it.
- `src/scantpaper/tools_menu_mixins.py` and
  `src/scantpaper/scan_menu_item_mixins.py`: construct, store, and pass the
  setting.
- `src/scantpaper/config.py`: default `"tessdata directory": ""`.
- `src/scantpaper/app_window.py`: the startup locale language check uses the
  same guarded path resolution.
- Tests, `README.md`, and `po/scantpaper/*.po` (new strings marked `#, fuzzy`).
- No database schema change, no new dependencies, no change to the OCR image
  pipeline.
