## 1. Core Implementation

- [x] 1.1 Add `Page.to_stored_bytes()` in `page.py` (replacing the unused `to_bytes()`): returns PNG for `mode == "1"`, original file bytes for JPEG/PNG sources, PNG for images with an alpha channel, and JPEG q92 otherwise; add `Page._stored_bytes` populated at construction for compact formats only
- [x] 1.2 Change `_insert_image` (docthread.py:284) to call `page.to_stored_bytes()` instead of `page.to_bytes()` for new imports
- [x] 1.3 In `get_pixbuf_at_scale` (page.py:307), downscale the PIL image to the target box before saving to the temp file (keep `.load()` and the `_prepare_scale` sizing)
- [x] 1.4 In `Page.from_bytes` (page.py:103), stash the stored blob on the page (`_stored_bytes`); the stored format is read from `image_object.format`
- [x] 1.5 In `write_image_for_pdf` (page.py:359), write the stored JPEG bytes to the temp `.jpg` file when the stored format is JPEG and no downsampling/compression options apply; keep the existing PNG path otherwise

## 2. Tests

- [x] 2.1 Test that a grayscale TIFF import stores a JPEG blob (decode the stored blob, assert `format == "JPEG"`)
- [x] 2.2 Test that a 1-bit page import stores a PNG blob (lossless)
- [x] 2.3 Test that importing a JPEG file stores the original bytes unmodified (byte equality)
- [x] 2.4 Test that importing a PNG file stores the original bytes unmodified
- [x] 2.5 Test that `get_pixbuf_at_scale` produces a valid thumbnail and that no full-size image is encoded (assert on dimensions of the temp-file image if instrumented, or via a spy on `Image.save`)
- [x] 2.6 Test that `write_image_for_pdf` with no options writes the stored JPEG bytes through (byte equality with the stored blob)
- [x] 2.7 Test that `write_image_for_pdf` with downsampling/compression options still re-encodes (output differs from stored blob / valid PNG)
- [x] 2.8 Test that a session with pre-existing PNG blobs still loads and displays (regression guard for mixed-format DB)

## 3. Docs and verification

- [x] 3.1 Document the import/save behaviour change in README.md
- [x] 3.2 Run the full test suite (`pytest`) and confirm no regressions
- [x] 3.3 Format with `black` and confirm the `pylint` score and coverage are the same or better than before the change
