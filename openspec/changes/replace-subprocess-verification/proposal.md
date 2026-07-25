## Why

The test suite spawns 72 subprocess calls (pdfinfo, identify, cat, pdftotext, etc.) to verify output correctness. Each subprocess call adds ~50-100ms of overhead (process spawn + exec). Replacing these with Python-native libraries (pikepdf for PDFs, PIL for images, file reads for text) eliminates that overhead, saving an estimated ~3s of wall time and making tests more debuggable.

## What Changes

- Replace `cat` subprocess calls (12 calls in test_151_save_text.py, test_121_save_djvu.py) with Python `open().read()`
- Replace `pdfinfo` subprocess calls (16 calls in test_1111, test_1162, test_131) with `pikepdf` page/metadata queries
- Replace `identify` subprocess calls (19 calls in test_1111, test_1611, test_121, test_131, test_141) with `PIL.Image.open()` properties
- Keep `djvused`, `djvutxt`, `djvudump`, `pdfimages`, `pdffonts`, `pdftotext`, `gs`, and `convert txt:-` as subprocess calls (no viable Python replacements)

## Capabilities

### New Capabilities

None — this is a test infrastructure change with no user-facing behavior changes.

### Modified Capabilities

None — no existing specs are affected.

## Impact

- **Test files modified**: test_1111_save_pdf.py, test_1162_save_multipage_pdf.py, test_1611_import_tiff.py, test_121_save_djvu.py, test_131_save_tiff.py, test_141_save_image.py, test_151_save_text.py
- **Dependencies**: pikepdf and Pillow (already in pyproject.toml)
- **Test behavior**: No change in what is verified — only the mechanism changes from subprocess to Python API
- **Estimated time savings**: ~3s wall time (from ~98s to ~95s)
