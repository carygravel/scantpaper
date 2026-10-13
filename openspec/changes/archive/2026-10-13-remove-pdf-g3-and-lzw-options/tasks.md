## 1. Remove the PDF options

- [x] 1.1 Remove the `lzw` and `g3` rows from `PDF_COMPRESSION_ALGS` in
      `src/scantpaper/dialog/save.py` and retarget `_JBIG2_ALG_INDEX` so
      JBIG2 is still inserted directly after G4 in the shorter list
- [x] 1.2 Drop the `g3` alias from `resolve_pdf_codec` in
      `src/scantpaper/page.py` (the branch becomes `"g4"` only); confirm
      `lzw` still resolves to Flate through the non-`auto` fallback
- [x] 1.3 In `src/scantpaper/tests/test_dialog_save.py`, assert
      `pdf_compression_algs()` no longer lists `lzw`/`g3`, still lists
      `g4`/`png`, and still inserts `jb2` immediately after `g4` when the
      encoder is available
- [x] 1.4 In `src/scantpaper/tests/test_04_page.py`, drop the `g3` and
      `lzw` parameters from `test_resolve_pdf_codec` (the `g4` and `png`
      cases remain)

## 2. Migrate stored preferences

- [x] 2.1 In `src/scantpaper/config.py`, add a migration in
      `_deserialise_and_migrate` that maps a stored `pdf compression` of
      `lzw` to `png` and `g3` to `g4`, logging the change
- [x] 2.2 In `src/scantpaper/tests/test_8_config.py`, assert the migration
      maps `lzw` → `png` and `g3` → `g4`, and leaves a valid value such as
      `auto` unchanged

## 3. Update tests that used the PDF LZW/G3 options

- [x] 3.1 In `src/scantpaper/tests/test_dialog_save.py`, change
      `test_pdf_compression_changed_callback` to use a still-valid
      non-quality option (e.g. `g4`) for the "hide quality" assertion
- [x] 3.2 In `src/scantpaper/tests/test_052_dialog_save.py`, change the
      PDF compression callback assertions from `lzw` to `g4`; leave the
      TIFF `lzw` assertions unchanged

## 4. Documentation

- [x] 4.1 Update the README Save section option list to remove **LZW** and
      **G3**, leaving G4, Flate, JPEG, JPEG 2000 and None (plus JBIG2)
- [x] 4.2 Add a changelog entry under the unreleased version

## 5. Verification

- [x] 5.1 Run `ruff format --check src/scantpaper/`, `ruff check
      src/scantpaper/` and `ty check .`
- [x] 5.2 Run the full `pytest` and confirm the 99% coverage gate passes
      with no touched file worse than before
- [x] 5.3 Run `PYTHONPATH=src python3 dev/generate_pot.py` and
      `PYTHONPATH=src python3 dev/check_po.py`; confirm no new advisory and
      that the `LZW`/`G3`/Group 3 msgids remain (TIFF still uses them)
