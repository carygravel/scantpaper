# Tasks

## 1. Version gate

- [x] 1.1 Add a module-level helper in `savethread.py` that parses
  `ocrmypdf.__version__` into its leading `(major, minor)` and reports whether
  the every-save lossless request applies (>= 17.6), treating an unparseable
  version as the older branch; verify with unit tests covering a release
  string, a pre-release string such as `17.6.0rc1`, and a malformed string.

## 2. Request the lossless PDF/A conversion

- [x] 2.1 Record in `_assemble_pdf` whether any page image was written with a
  non-JPEG codec and pass it to `_embed_text_layer`; verify with a unit test
  that the flag is set for a Flate save and clear for a JPEG-only save.
- [x] 2.2 Choose the `pdfa_image_compression` value in `_embed_text_layer` from
  the version gate and the flag, and pass it to
  `ocrmypdf.api._hocr_to_ocr_pdf`; verify with unit tests asserting the value
  is `lossless` for a lossless save on both branches, and omitted for a
  JPEG-only save on the older branch.
- [x] 2.3 Add an end-to-end save test asserting a Flate save yields a Flate
  page image in the output PDF and a JPEG-only save yields JPEG; verify by
  inspecting the embedded image filter the way the existing PDF tests do.

## 3. Documentation

- [x] 3.1 Document in `README.md` that a lossless compression choice is
  preserved through PDF/A regardless of OCRmyPDF version; verify the wording
  matches the tested behaviour.

## Workflow follow-up

- Archive the change once review is complete.
