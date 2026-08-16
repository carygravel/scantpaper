## Why

OCR of a scanned page takes roughly 15–19 seconds, and only ~15s of that is tesseract itself. The gap is overhead around it: `do_tesseract` re-encodes the page image to a temporary PNG (~4.1s), writes it to disk, runs `ProcessPages` (which also writes the hOCR result to disk and re-reads it), and finally saves the OCR result through the image byte-compare/re-insert path — even though OCR never changes the page pixels. Users OCR entire archives, so this per-page overhead multiplies. We already removed the PNG re-encode for storage (compact-image-blobs); now we remove the PNG encode + disk round-trip for OCR input, and stop treating OCR as an image-changing operation.

## What Changes

- `do_tesseract` feeds the page's in-memory pixels to tesseract directly via `SetImageBytes(...)` + `Recognize()` + `GetHOCRText(0)` instead of saving a temporary PNG and re-reading the `image_out.hocr` file. This removes the ~4.1s PNG encode, the temp file write, and the disk round-trip of the hOCR output. The exact stored pixels are recognized — no decode/re-encode drift.
- OCR reuses the page's existing stored image id directly instead of byte-comparing the image blob and re-inserting the image row. Only the text layer and OCR metadata change. Undo/redo still work: a new page row (holding the new text layer) is still created for the action snapshot.
- The `replace_page` entry point gains a way to skip the image round-trip for pixel-preserving operations (OCR being the first caller).
- No new Python dependencies. Tesserocr is already a dependency; `Pillow`'s `tobytes()` provides the raw pixel buffer (numpy is not required).

## Capabilities

### New Capabilities
- `ocr-recognition`: Generating a searchable text layer for a scanned page using tesseract, including how the page image is fed to the OCR engine, how the resulting hOCR text is imported into the page, and how the operation preserves the stored page image.

### Modified Capabilities
<!-- None: image-storage-format requirements are unchanged; OCR simply reuses the already-stored image. -->

## Impact

- `scantpaper/docthread.py`: `do_tesseract` (hOCR generation without temp file), `replace_page` (optional image-reuse path).
- `scantpaper/tests/test_docthread.py`: update mocked `ProcessPages`/`Path` assertions for the in-memory API.
- `scantpaper/tests/test_411_tesseract.py`: real-OCR integration test continues to verify OCR quality/equivalence.
- No database schema change. No new dependency.
