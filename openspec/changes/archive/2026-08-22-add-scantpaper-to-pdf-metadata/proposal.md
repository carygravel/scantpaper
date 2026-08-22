## Why

PDFs saved by scantpaper carry no trace of the application that produced them.
The save pipeline already brands the intermediate PDF with
`/Creator: scantpaper v<version>` via img2pdf, but ocrmypdf's metadata stage
discards `/Creator` and hardcodes its own toolchain string
(`OCRmyPDF <ver> / Tesseract OCR-hOCR <ver>`, plus `pikepdf <ver>` as
`/Producer`), and offers no option or plugin hook to change this. As a result,
metadata shown by PDF tools credits only the underlying libraries - and
inconsistently so: when text-layer embedding fails, the fallback path copies
the intermediate PDF, which *does* retain scantpaper branding.

## What Changes

- After ocrmypdf embeds the text layer, a pikepdf post-save pass prepends
  `scantpaper v<version> / ` to whatever Creator string ocrmypdf produced,
  yielding e.g.
  `Creator: scantpaper v3.0.16 / OCRmyPDF 16.13.0+dfsg1 / Tesseract OCR-hOCR 5.5.0`
  while preserving full provenance of the OCR toolchain.
- The same pass keeps document info and XMP metadata consistent
  (`/Creator` and `xmp:CreatorTool`), as required for PDF/A output.
- `/Producer` is left untouched (it honestly names the library that last wrote
  the file).
- The existing placeholder-title removal pass is generalised into this single
  metadata fixup pass, so no extra file rewrite is needed in the common case.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `save-pdf-metadata`: adds a requirement that saved PDFs identify scantpaper
  in their Creator metadata, alongside the existing title requirements.

## Impact

- `scantpaper/savethread.py`: `_remove_pdf_title` becomes a generalised
  post-embed metadata fixup; called unconditionally on successful embed
  instead of only when no user title was given.
- Tests: new assertions on Creator strings; existing title tests keep passing.
- No new dependencies (pikepdf is already used).
- User-visible: PDF metadata of every saved PDF changes (intended).
