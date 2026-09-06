## 1. Thumbnail generation implementation

- [x] 1.1 In `scantpaper/page.py:get_pixbuf_at_scale`, replace the single
      `Image.Resampling.BOX` resize with a two-step decimate-then-resample:
      compute a decimation factor to bring the larger dimension to roughly twice
      the target (`Image.reduce`), then `Image.resize((w, h), resample=Image.Resampling.LANCZOS)`
      to the exact `_prepare_scale` size.
- [x] 1.2 Preserve the existing `mode == "I"` → `"L"` conversion and the
      `_prepare_scale` resolution-ratio sizing; keep writing the resized
      thumbnail to a temp PNG and loading it via `GdkPixbuf.Pixbuf.new_from_file_at_scale`.
- [x] 1.3 Keep thumbnails within the `THUMBNAIL` (100 px) box, resizing small
      source images to fill the box (existing behaviour).

## 2. Tests

- [x] 2.1 Update/extend `scantpaper/tests/test_04_page.py` so
      `test_get_pixbuf_at_scale_downscales_before_save` still verifies the saved
      image is downscaled to exactly (100, 100) before writing.
- [x] 2.2 Add a test asserting the two-step path calls `Image.reduce` then a
      LANCZOS resize, and that the final pixbuf dimensions respect the
      `_prepare_scale` box and aspect ratio (including a non-uniform x/y
      resolution case).
- [x] 2.3 Add a test that a source image smaller than the thumbnail box is
      resized to fill it.
- [x] 2.4 Run the thumbnail-related tests: `pytest scantpaper/tests/test_04_page.py`

## 3. Verification

- [x] 3.1 Run the full test suite `pytest` and confirm coverage thresholds still
      pass.
- [x] 3.2 Run `ruff format` and `ruff check` on changed files and confirm no new
      lint errors.
- [x] 3.3 If a scanner/test image is available, generate a thumbnail from a
      high-DPI scan and visually confirm it is sharper than the previous BOX
      output. Verified programmatically on a dense 2000x2800 text page: the
      new thumbnail has higher edge-gradient energy than the BOX equivalent
      at the same dimensions.
- [x] 3.4 Document the user-visible thumbnail quality improvement in README.md
      if applicable.