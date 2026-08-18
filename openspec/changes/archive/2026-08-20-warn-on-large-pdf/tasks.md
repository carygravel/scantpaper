## 1. Roll back 2 GiB workarounds

- [x] 1.1 Remove `_ENGINE_THRESHOLD`, `_PIXEL_BPP`, `_estimate_page_pdf_size` from savethread.py (they will be re-added in step 2 in a simpler form)
- [x] 1.2 Remove `skip_pdfa` and `fast_web_view` logic from `_embed_text_layer`; restore the plain `_hocr_to_ocr_pdf` call with `optimize=0` and `plugins=["savethread"]`
- [x] 1.3 Remove `linearize` parameter from `_remove_pdf_title`; restore the unconditional `pdf.save(path, preserve_pdfa=True, linearize=True)` call
- [x] 1.4 Remove the output-validation block (`pikepdf.open` check after ocrmypdf) from `_embed_text_layer`
- [x] 1.5 Remove the `estimated_size` accumulation and engine-selection logic from `do_save_pdf`
- [x] 1.6 Remove the large-PDF test (`test_save_pdf_large_uses_internal_engine`) and the small-PDF engine/linearize assertions from `test_save_pdf`

## 2. Add size estimation and early rejection

- [x] 2.1 Add `_2GIB` constant and `_PIXEL_BPP` mapping to savethread.py
- [x] 2.2 Add `_estimate_page_pdf_size(image, temp_filename, opts)` helper (JPEG passthrough detection, pixel-format fallback)
- [x] 2.3 In `do_save_pdf`, initialise `estimated_size = 0` and `opts` before the page loop; accumulate per-page estimates inside the loop
- [x] 2.4 After the page loop, if `estimated_size >= _2GIB`: remove temp files, raise `RuntimeError` with translated message including the size in GiB
- [x] 2.5 Add test verifying that a save with estimated size ≥ 2 GiB raises RuntimeError and cleans up temporaries

## 3. Document known limitations

- [x] 3.1 Add a "Known Limitations" section to README.md documenting the three 32-bit overflow bugs (img2pdf linearization, Ghostscript PDF/A, pikepdf xref-stream linearization) with thresholds, symptoms, and what to re-test when dependencies update

## 4. Verify

- [x] 4.1 Run `pytest` — all tests pass
- [x] 4.2 Run `black` — no formatting changes needed
- [x] 4.3 Run `pylint` — score same or better than baseline (savethread 8.33)
- [x] 4.4 Coverage: uncovered and partially-covered lines same or better
