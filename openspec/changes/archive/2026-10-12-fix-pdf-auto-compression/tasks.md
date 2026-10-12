## 1. Persist image provenance

- [x] 1.1 Bump `USER_VERSION` to 3 in `src/scantpaper/const.py`.
- [x] 1.2 Add an `original INTEGER DEFAULT 0` column to the `image` table
  creation in `docthread.py`, and an `open()` migration for user_version 2
  that adds the column and advances the version.
- [x] 1.3 Mark the column when inserting an image whose bytes are the original
  import (`Page` constructed from an imported file), and leave it unset for
  images inserted from a generated encode.
- [x] 1.4 Surface the flag on `Page` (set in `from_bytes`/`get_page`, cleared
  by any re-encoding path) so the save thread can read it.

## 2. Resolve `auto` and encode correctly

- [x] 2.1 Add a helper that resolves a page's colour model and the selected
  compression option to a concrete codec (G4 / JPEG / Flate), implementing the
  `auto` table from `specs/pdf-image-compression`.
- [x] 2.2 Change `Page.write_image_for_pdf` to choose the temp-file format from
  the resolved codec, writing a 1-bit PBM for G4 and a `.png` for Flate.
- [x] 2.3 Encode generated continuous-tone pages as JPEG at the configured
  quality; keep the original-import passthrough for JPEG inputs.
- [x] 2.4 Make explicit options map correctly: `jpg` -> JPEG at quality,
  `png`/`lzw` -> Flate, `g3`/`g4` -> G4, `auto` -> resolved table.
- [x] 2.5 Verify against `img2pdf` (PBM/G4-TIFF -> CCITTFaxDecode, JPEG ->
  DCTDecode, PNG -> FlateDecode) and adjust the temp suffix accordingly.

## 3. Save options plumbing

- [x] 3.1 Confirm `quality` and `compression` reach `write_image_for_pdf`
  through `savethread.py` and the `_save_pdf` option dict; fix any missing key.
- [x] 3.2 Ensure the save dialog's quality value is used for PDF output, not
  only TIFF.

## 4. Tests

- [x] 4.1 Unit-test the codec resolver for bilevel, grayscale, RGB, CMYK and
  alpha images across `auto`, `jpg`, `png`, `lzw`, `g3`, `g4`.
- [x] 4.2 Integration-test that an `auto` save of a bilevel page extracts a
  1-bit CCITT Group 4 image (`pdfimages`/`pikepdf`), and update the existing
  `g4` tests to assert the filter, not just the bit depth.
- [x] 4.3 Integration-test that an `auto` save of a generated colour/grayscale
  page embeds DCTDecode, and that lowering the quality shrinks the stream.
- [x] 4.4 Integration-test that an imported JPEG saved with `auto` embeds the
  original bytes verbatim.
- [x] 4.5 Test the schema migration from user_version 2 to 3 and that old
  session blobs load.

## 5. Documentation and verification

- [x] 5.1 Update `README.md` to describe the `auto` behaviour and that the JPEG
  quality setting now affects PDF output.
- [x] 5.2 Regenerate the translation template if any translated string
  changed (`dev/generate_pot.py`), marking any new `.po` entries `#, fuzzy`.
- [x] 5.3 Run `pytest`, `ruff format`, `ruff check`, and `ty check .`; confirm
  no new uncovered lines and no new lint/type diagnostics.
