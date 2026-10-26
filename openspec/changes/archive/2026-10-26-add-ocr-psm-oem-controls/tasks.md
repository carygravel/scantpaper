# Tasks

## 1. Settings

- [x] 1.1 Add `"ocr psm"` (empty means automatic) and `"ocr engine mode"`
  (`"default"`) to `DEFAULTS` in `config.py`. Verify with a config test that a
  file without the keys loads with the defaults and that the values round-trip.

## 2. Engine initialisation

- [x] 2.1 Apply the page segmentation mode with `api.SetPageSegMode(...)`
  after `api.InitFull(...)` in `DocThread.do_tesseract`, and pass the stored
  engine mode as `InitFull(oem=...)`, defaulting to the current behaviour.
  Verify with worker tests against a fake tesserocr API asserting both calls
  for a chosen segmentation and engine mode, and no change for the defaults.
- [x] 2.2 Wrap an initialisation failure caused by the engine mode so the
  raised error names the engine mode instead of tesserocr's "invalid tessdata
  path", before `Recognize` runs and before any page is modified. Verify with
  a test that a failing `InitFull` produces the named-mode error and leaves the
  page unchanged.

## 3. Controls and persistence

- [x] 3.1 Add a page segmentation mode combo to `OCRControls`, offering the
  curated tesseract modes with the automatic mode selected by default, stored
  numerically, with an unrecognised stored value falling back to automatic.
  Verify with widget tests for the default, a selection, and a fallback.
- [x] 3.2 Add an engine mode combo (default, LSTM only, legacy, combined) to
  `OCRControls`. Verify with widget tests for the default and a selection, and
  for the value surviving a settings reload.
- [x] 3.3 Persist and restore both settings from the scan window and the
  Tools -> OCR dialog, forwarding them to `ocr_pages` alongside the existing
  OCR options. Verify with tests asserting the stored settings and the
  forwarded keyword arguments in both flows.
- [x] 3.4 Reject `tessedit_pageseg_mode` and `tessedit_ocr_engine_mode` in
  `OCRControls.validation_error` with a message directing the user to the
  corresponding control. Verify with tests asserting the message for each
  name.
- [x] 3.5 Document the two controls in the README. Verify the documented
  labels match those used in the controls.

## 4. Translations

- [x] 4.1 Regenerate the translation template with
  `PYTHONPATH=src python3 dev/generate_pot.py`, add any new strings to
  `po/scantpaper/*.po` as `#, fuzzy` entries only, and run
  `PYTHONPATH=src python3 dev/check_po.py` until it reports no catalog
  problems.

## 5. Integration verification

- [x] 5.1 Run a real-engine smoke test of the default path (no segmentation or
  engine mode chosen) to confirm existing behaviour is unchanged.
- [x] 5.2 Run `ruff format`, `ruff check`, `ty check .`, and the full `pytest`
  suite; confirm they pass and coverage has not regressed.
- [x] 5.3 Run `openspec validate add-ocr-psm-oem-controls --strict` and fix any
  reported problems.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
