## 1. Core Implementation in do_save_pdf

- [x] 1.1 In `do_save_pdf` (savethread.py:126-138), add per-page progress reporting to the image-write loop: increment a 1-based page counter per iteration and emit `request.data(i / (len(list_of_pages) + 1))` followed by `request.data(_("Writing page %i of %i") % (i, len(list_of_pages)))`, mirroring `do_save_djvu`
- [x] 1.2 Add `request.data(_("Writing PDF"))` immediately before the `img2pdf.convert()` call (line 150)
- [x] 1.3 Remove the mislocated per-page progress reporting from the hocr-write loop (lines 171-178), keeping `self.check_cancelled()` in place
- [x] 1.4 Verify the resulting progress sequence in `do_save_pdf`: "Setting up PDF" -> per-page "Writing page i of n" -> "Writing PDF" -> "Embedding text layer" -> ocrmypdf progress -> final `request.data(1.0)`

## 2. Tests

- [x] 2.1 Extend `test_save_pdf_with_progress_hooks` or add a new test in `scantpaper/tests/test_savethread.py` asserting that `request.data` is called with the per-page fraction and "Writing page" message during the image-write loop
- [x] 2.2 Add an assertion that `request.data` is called with "Writing PDF" before `img2pdf.convert` runs
- [x] 2.3 Add/assert that no "Writing page" message is emitted after `img2pdf.convert` (i.e. during the hocr loop)

## 3. i18n, docs, and verification

- [x] 3.1 Regenerate the translation template with `dev/generate_pot.py` so the new "Writing PDF" string is present for upload to Rosetta (do NOT edit `po/*.po` files directly — translations are downloaded from Rosetta before release)
- [x] 3.2 Document the user-visible change in README.md if there is no existing mention of save progress behaviour
- [x] 3.3 Run the full test suite (`pytest`) and confirm no regressions
- [x] 3.4 Format with `black` and confirm the `pylint` score and coverage are the same or better than before the change
