## 1. TDD: Unit tests for `-list` parsing

- [x] 1.1 Write failing tests in `scantpaper/tests/test_importthread.py` for a new module-level `_parse_pdfimages_list()`: parses a `pdfimages -list` capture with header, separator, and data lines into entries containing `page`, `num`, `type`, `x_ppi`, `y_ppi`; skips header and separator lines; a single data line yields one entry (per D1)
- [x] 1.2 Write failing tests that `_parse_pdfimages_list()` yields an entry for `image`, `smask`, and `stencil` types, and returns an empty list for header-only output (vector-only page)

## 2. Implement `_parse_pdfimages_list`

- [x] 2.1 Implement `_parse_pdfimages_list(out)` in `scantpaper/importthread.py` per design D1 (whitespace split, data line detected by integer first two tokens, returns `list[dict]`), then confirm 1.1/1.2 pass

## 3. TDD: Tests for `_do_import_pdf` behavior

- [x] 3.1 Write a failing test in `test_importthread.py` that a page whose `-list` has one `image` + one `smask` entry imports exactly one page from the `image` entry and removes the extracted `smask` file (mock `subprocess.check_output`, `subprocess.run`, `glob.glob`, `importthread.Page`)
- [x] 3.2 Write failing tests that the one-image-per-page warning is raised when two `image` entries are on a page, but not for a single `image` + `smask` pair (per D4)
- [x] 3.3 Write a failing test that the imported page's resolution comes from its own `-list` entry when image and smask report different ppi (per D2)
- [x] 3.4 Write a failing test for the count-mismatch fallback: when extracted file count differs from `-list` entry count, all files are imported and a warning is raised (per D2)
- [x] 3.5 Write a failing test that leftover `x-*` files from a previous page are removed before the next page is imported (per D3)

## 4. Rework `_do_import_pdf`

- [x] 4.1 Rework `_do_import_pdf` in `scantpaper/importthread.py` to use `_parse_pdfimages_list`, correlate extracted files with entries by sorted index, skip non-`image` entries (removing their files), use each entry's own resolution, set the warning from the non-mask image count, and clean up leftover `x-*` files each iteration; confirm 3.1-3.5 pass
- [x] 4.2 Confirm the existing tests `test_get_pdf_images_error` and `test_import_pdf_image_error` still pass (error paths unchanged)

## 5. Regression test for the reported issue

- [x] 5.1 Add a test that builds a PDF from a transparent image (e.g. with `img2pdf`), imports it into a `Document`, and asserts exactly one page is created and no spurious warning is raised (mirrors the issue #43 repro with the repo's `dog.png`/`dog.pdf`)

## 6. Verification

- [x] 6.1 Run the full suite with `pytest` and confirm all tests pass
- [x] 6.2 Run `black` and `pylint` on the changed files and confirm scores do not regress
- [x] 6.3 Add a note to `changelog.md` describing the fix for opening PDFs created from transparent images
