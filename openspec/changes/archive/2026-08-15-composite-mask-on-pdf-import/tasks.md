## 1. TDD: Unit tests for `_composite_over_white`

- [x] 1.1 Write failing tests in `scantpaper/tests/test_importthread.py` for a new module-level `_composite_over_white(image_path, mask_path)` using real PPM files in `tmp_path`: a fully opaque mask pixel keeps the image value, a fully transparent pixel becomes white, and a 50% pixel blends to the midpoint (per D1/D3)
- [x] 1.2 Write failing tests that a color image composites per channel, and that a mask whose size differs from the image returns `False` and leaves both files untouched (fallback, per D3)

## 2. Implement `_composite_over_white`

- [x] 2.1 Implement `_composite_over_white(image_path, mask_path)` in `scantpaper/importthread.py` using `PIL.Image.composite` over a white background, saving in place; then confirm 1.1/1.2 pass

## 3. TDD: Tests for pairing and import behavior

- [x] 3.1 Write a failing test that `_correlate_pdf_images` returns the extracted mask filename paired with an `image` entry whose `smask` immediately follows it in the `-list`, and that the mask file is NOT deleted at correlation time (per D2/D3)
- [x] 3.2 Write failing tests that an `image` with no following `smask` is unpaired (`mask_fname` is `None`), that `stencil` files and unpaired `smask` files are still removed, and that the count-mismatch fallback returns unpaired entries (per D2)
- [x] 3.3 Write a failing test that `_do_import_pdf` on a page with `image`+`smask` imports exactly one page whose file content is the composite (provide real PPM files via mocked `subprocess`/`glob`; verify the `Page`'s opened image equals the expected composite)
- [x] 3.4 Confirm existing behavior tests (`test_import_pdf_skips_smask`, `test_import_pdf_no_warning_for_smask`, `test_import_pdf_warning_for_two_images`, `test_import_pdf_resolution_from_own_entry`, `test_import_pdf_count_mismatch_fallback`, `test_import_pdf_cleans_up_leftover_files`) still pass with the compositing flow, updating their mocks/assertions as needed

## 4. Rework the import flow

- [x] 4.1 Rework `_correlate_pdf_images` in `scantpaper/importthread.py` to return `(fname, x_ppi, y_ppi, mask_fname)` tuples, pairing each `image` with an immediately-following `smask`, keeping paired mask files and removing unpaired non-image files (per D2/D4/D5)
- [x] 4.2 Rework `_import_pdf_images` to composite a paired image over white before creating the `Page` and to remove the mask file afterwards, falling back to the raw image when compositing fails; confirm 3.1-3.4 pass

## 5. Regression test for the reported issue

- [x] 5.1 Extend `test_import_pdf_from_transparent_image_creates_one_page` in `scantpaper/tests/test_1111_save_pdf.py` to assert that the imported page's pixels equal the composite of the source transparent PNG over white (end-to-end, mirrors the user's dog.pdf observation)

## 6. Verification

- [x] 6.1 Run the full suite with `pytest` and confirm all tests pass
- [x] 6.2 Run `black` and `pylint` on the changed files and confirm scores do not regress
- [x] 6.3 Add a note to `changelog.md` describing that importing a PDF page with a soft mask now composites the image with its mask
