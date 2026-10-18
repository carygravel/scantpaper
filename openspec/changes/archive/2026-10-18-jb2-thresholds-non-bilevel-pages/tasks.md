## 1. Tests first (TDD)

- [x] 1.1 Update `test_resolve_pdf_codec` parametrize in
  `src/scantpaper/tests/test_04_page.py`: `("L", "jb2")`,
  `("RGB", "jb2")`, `("CMYK", "jb2")` expect `PDF_CODEC_G4` (bilevel
  `("1", "jb2")` stays `PDF_CODEC_G4`; alpha stays `PDF_CODEC_FLATE`)
- [x] 1.2 Update the float-quality `jb2` test to assert a 1-bit PNM
  (P4) stream is written instead of a JPEG stream, and add a test that
  saving the same page with `jb2` at two different quality values
  produces identical embedded images
- [x] 1.3 Add a test that saving a grayscale or colour page with `jb2`
  and with `g4` extracts as 1-bit images produced by the same bilevel
  conversion (mirror of the `g4` threshold path)

## 2. Implementation

- [x] 2.1 In `src/scantpaper/page.py` `resolve_pdf_codec`, map
  `compression == PDF_CODEC_JBIG2` to
  `_codec_for_colour_model(image, PDF_CODEC_G4)`; update the function
  docstring accordingly
- [x] 2.2 Run `pytest` and confirm the suite passes with coverage at
  or above the configured threshold

## 3. Documentation and gates

- [x] 3.1 Update `README.md` (PDF compression section, ~line 170) to
  state that the JBIG2 option thresholds non-bilevel pages like G4 and
  wraps at 80 characters
- [x] 3.2 Run `ruff format`, `ruff check` and `ty check .` and resolve
  any diagnostics without suppressions
