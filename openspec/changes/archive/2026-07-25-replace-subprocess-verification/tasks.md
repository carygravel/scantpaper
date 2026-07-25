## 1. Replace `cat` subprocess calls with Python file reads

- [x] 1.1 Replace `cat` calls in `test_151_save_text.py` (11 calls) with `open().read()`
- [x] 1.2 Replace `cat` call in `test_121_save_djvu.py` (1 call) with `open().read()`

## 2. Replace `pdfinfo` subprocess calls with pikepdf

- [x] 2.1 Replace `pdfinfo` page-size checks in `test_1111_save_pdf.py` with pikepdf MediaBox queries (lines 68, 114, 164, 237, 763, 799)
- [x] 2.2 Replace `pdfinfo -isodates` metadata checks in `test_1111_save_pdf.py` with pikepdf docinfo queries (lines 576, 621)
- [x] 2.3 Replace `pdfinfo` encryption check in `test_1111_save_pdf.py` with pikepdf PasswordError (line 258)
- [x] 2.4 Replace `pdfinfo` page-count checks in `test_1162_save_multipage_pdf.py` with pikepdf len() queries (lines 182, 213, 245, 277, 315)
- [x] 2.5 Replace `pdfinfo` check in `test_131_save_tiff.py` with pikepdf query (line 201)

## 3. Replace `identify` subprocess calls with PIL.Image

- [x] 3.1 Replace `identify` format/dimension checks in `test_141_save_image.py` with PIL.Image.open() (4 calls)
- [x] 3.2 Replace `identify` checks in `test_131_save_tiff.py` with PIL.Image.open() (4 calls — skip `file` command)
- [x] 3.3 Replace `identify` checks in `test_1611_import_tiff.py` with PIL.Image.open() (2 calls)
- [x] 3.4 Replace `identify` checks in `test_121_save_djvu.py` with PIL.Image.open() (1 call)
- [x] 3.5 Replace `identify` checks in `test_1111_save_pdf.py` where PIL covers the property (skip pdfimages→identify pipelines, keep gs→convert pipeline)

## 4. Verify

- [x] 4.1 Run `pytest` and confirm all tests pass with identical coverage
- [x] 4.2 Run `black --check` and `pylint` to confirm code quality
