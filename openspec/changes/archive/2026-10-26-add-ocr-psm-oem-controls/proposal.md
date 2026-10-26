# Proposal

## Why

Page segmentation mode and OCR engine mode are engine-initialisation arguments
in tesseract, not parameters the advanced field can apply. Users try them
because `tesseract --help-extra` lists `--psm` and `--oem`, and today the field
either rejects the flag or accepts a parameter name that does nothing:
`tessedit_pageseg_mode=6` passes validation but is overwritten back to the
automatic mode when the engine is initialised, and `tessedit_ocr_engine_mode`
can make initialisation fail with a misleading "invalid tessdata path" error.

## What Changes

- Add a **Page segmentation mode** selector to the OCR controls, listing
  tesseract's modes (automatic, single block, single line, single word, sparse
  text, and the rest), defaulting to the current automatic behaviour.
- Add an **OCR engine mode** selector (default, LSTM only, legacy, combined),
  defaulting to the current default.
- Apply the selected modes when the engine is initialised and persist them
  alongside the existing OCR settings.
- Reject `tessedit_pageseg_mode` and `tessedit_ocr_engine_mode` in the
  advanced field with a message that points at these controls, instead of
  accepting values that are ignored or that break initialisation.

## Capabilities

### New Capabilities

<!-- None: this extends the existing OCR interface. -->

### Modified Capabilities

- `ocr-recognition`: the OCR interface gains page-segmentation and
  engine-mode selection, and stops accepting the parameter names those
  controls own.

## Impact

- `src/scantpaper/postprocess_controls.py`: the two new selectors, their
  persistence and validation.
- `src/scantpaper/docthread.py`: apply the selected modes when the engine is
  initialised.
- `src/scantpaper/document.py`, `src/scantpaper/tools_menu_mixins.py`,
  `src/scantpaper/scan_menu_item_mixins.py`, `src/scantpaper/config.py`:
  forward and persist the new settings.
- `README.md`: document the two controls.
- `po/scantpaper/*.po`: new UI strings, marked `#, fuzzy`.
- `src/scantpaper/tests/`: cover the selectors, their persistence, and the
  rejection of the corresponding parameter names.
- No new dependency and no database schema change.

## Notes

Builds on the corrective-message behaviour proposed in
`clarify-ocr-engine-options`; the two changes can land independently, and this
one narrows the `--psm`/`--oem` guidance from "no parameter exists" to "use the
control".
