## Context

See proposal.md — Why. OCR currently runs in `DocThread.do_tesseract` (docthread.py:1263). The current flow:

1. Write `page.image_object` to a temp `.png` (`page.image_object.save(file.name)`) — ~4.1s for a continuous-tone A4 page.
2. `api.ProcessPages(output, file.name)` — tesseract reads the file, then writes the hOCR result to `image_out.hocr` on disk.
3. Re-read `image_out.hocr` from disk and unlink it.
4. `page.import_hocr(hocr)` sets the text layer; `ocr_flag`/`ocr_time` are set.
5. `self.replace_page(page, page.id)` — takes an action snapshot, byte-compares the image via `_insert_image(page, if_different_from=page.image_id)`, inserts a new page row (text + annotations), updates `page_order`, commits, and returns `(position, thumb, initial_page_id)` for the UI.

With the archived compact-image-blobs change, step 5's `to_stored_bytes()` returns the stored bytes directly for pages loaded via `from_bytes` (no re-encode), but `_insert_image` still `SELECT`s the full image blob and byte-compares it — waste for an operation that provably cannot change pixels.

Constraints that shape the design:
- No new Python dependencies (numpy is not in pyproject.toml).
- The undo/redo model stores one `page_order` snapshot per action; undoing OCR must restore the pre-OCR text layer, so OCR still needs a new `page` row pointing at the same `image` row.
- The OCR response must still return a thumbnail pixbuf — the UI consumes `(position, thumb, initial_page_id)`.
- `test_411_tesseract.py::test_tesseract_in_thread` runs real tesseract and asserts the recognized words, so OCR quality must be preserved.

## Goals / Non-Goals

**Goals:**
- Eliminate the temp-PNG encode, the temp image file, and the hOCR file write/read from `do_tesseract`.
- Skip the image blob `SELECT` + full-bytes compare for OCR, reusing the stored `image_id`.
- Keep undo/redo and the UI contract (`(position, thumb, initial_page_id)`) intact.
- Preserve recognition quality (same pixels, same 8-bit conversion tesseract already applies internally).

**Non-Goals:**
- Speeding up tesseract itself, or parallelizing OCR across pages (measured ceiling ~1.56×; separate concern).
- Changing the stored image format or database schema.
- Changing how PDF/DjVu save reads the text layer.

## Decisions

### D1: Feed in-memory pixels to tesseract via SetImageBytes
Replace the temp-file + `ProcessPages` + hocr-file-read block in `do_tesseract` with:

```python
with tesserocr.PyTessBaseAPI(lang=options["language"], path=path) as api:
    api.SetVariable("tessedit_create_hocr", "T")
    api.SetVariable("hocr_font_info", "T")
    image = page.image_object.convert("L")
    api.SetImageBytes(image.tobytes(), image.width, image.height, 1, image.width)
    api.Recognize()
    hocr = api.GetHOCRText(0)

page.import_hocr(hocr)
page.ocr_flag = True
page.ocr_time = datetime.datetime.now()
```

Rationale:
- `SetImageBytes(imagedata, width, height, bytes_per_pixel, bytes_per_line)` (tesserocr 2.11.0) accepts raw bytes; `Image.tobytes()` on an 8-bit `"L"` image gives a C-contiguous row-major buffer, so `bytes_per_pixel=1` and `bytes_per_line=width`. No numpy required.
- Always convert to `"L"` first: tesseract requires 8-bit input, PIL's `convert("L")` uses the ITU-R BT.601 luma coefficients — the same conversion tesseract applies internally when reading a PNG, so recognition quality is equivalent (verified by the real-OCR test). This also sidesteps ambiguity of raw bytes for `"1"` (bilevel) and other modes.
- `GetHOCRText(0)` after `Recognize()` returns the hOCR body fragment; it is wrapped in a full XHTML document (`<!DOCTYPE html>` + `<html>`/`<head>`/`<body>`) before `import_hocr`, because `Bboxtree.from_hocr` requires a `<body>` element. The hOCR variables (`tessedit_create_hocr`, `hocr_font_info`) are set as before so the word/confidence markup matches what `ProcessPages` produced.

Alternatives considered:
- `api.SetImage(page.image_object)` (tesserocr's PIL-aware setter): less explicit about mode/pixel layout; rejected in favor of the deterministic `"L"` + `SetImageBytes` path.
- `np.asarray(...)`: rejected — would add a numpy dependency.

### D2: Preserve pixels as an explicit operation
OCR feeds `page.image_object.convert("L")` — a derived 8-bit view, never a mutation of `image_object`. The stored image and `image_object` are untouched; only `text_layer`, `ocr_flag`, `ocr_time` change on the `page` object. This keeps requirement "OCR preserves the stored page image" trivially satisfiable and matches today's behavior.

### E1: Reuse the stored image on OCR via a `reuse_image` option
Add an optional `reuse_image=False` keyword to `replace_page` (docthread.py:399). When true:

```python
image_id = page.image_id
thumb = self._reuse_image_thumb(image_id)   # SELECT thumb FROM image WHERE id = ?
```

then proceed with the existing `_insert_page(page, image_id)` + `page_order` update + commit. `do_tesseract` calls `self.replace_page(page, page.id, reuse_image=True)`.

Rationale:
- `replace_page` already owns the snapshot/insert/commit choreography for pixel-changing ops; a keyword keeps one code path with a cheap branch. It preserves the undo model (snapshot + new page row) and the UI contract (returns `thumb`).
- `_reuse_image_thumb` reads only the small thumb blob and decodes it with `_bytes_to_pixbuf` — the same work `_insert_image` did on its reuse branch, minus the full-image `SELECT` and the multi-MB byte compare.

Alternatives considered:
- A separate `replace_page_ocr` method: rejected — duplicates the snapshot/insert/order/commit logic.
- Modifying `_insert_image` to accept the image id: rejected — it already takes a comparable; the branch belongs one level up in `replace_page`.

### D3: No signature/behavior change for non-OCR callers
All other `replace_page` callers (rotate, threshold, unpaper, brightness/contrast, negate, unsharp, crop, user-defined, save-HOCR) keep the default `reuse_image=False` path unchanged.

## Risks / Trade-offs

- **GetHOCRText vs ProcessPages output difference** → Both are driven by the same hOCR variables and parsed by `import_hocr`; guarded by the real-OCR integration test `test_411_tesseract.py::test_tesseract_in_thread`, plus the mocked unit tests updated to the new API.
- **Mode conversion changes OCR result** → `convert("L")` mirrors tesseract's internal conversion; the integration test asserts the recognized words survive. Color images may yield slightly different confidence in edge cases — acceptable and unlikely.
- **Memory** → The page image is already fully decoded in memory (`image_object`); the extra `"L"` copy is transient and roughly the image's raw size, comparable to the discarded temp-file path. No regression.
- **`SetImageBytes` argument correctness** → Bounded by unit tests mocking `PyTessBaseAPI` asserting the exact call, and by the real-OCR test.

## Migration Plan

No migration. The change is internal to the OCR pipeline; saved documents and the database schema are unaffected. Rollback is a revert of the `do_tesseract`/`replace_page` edits.

## Open Questions

None — the approach, specs, and task breakdown are settled. Remaining unknowns (exact hOCR byte differences, per-mode confidence) are verified by the existing test suite rather than blocking design.
