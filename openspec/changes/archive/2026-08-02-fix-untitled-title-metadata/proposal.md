## Why

PDFs saved by scantpaper with no title end up carrying a placeholder title
`'Untitled'` (visible in evince and re-imported into the session). The title is
injected by Ghostscript during ocrmypdf's PDF/A conversion, and ocrmypdf's
existing cleanup guard misses it because this Ghostscript writes `'Untitled'`
with literal apostrophes while the guard only matches bare `Untitled`. The
problem is unreported-fixed upstream (ocrmypdf issue #582 is closed but the fix
is incomplete; ocrmypdf's own regression test is failing on Fedora rawhide,
Red Hat bug #2458687), so scantpaper cannot wait for an upgrade and must handle
it itself.

## What Changes

- **Save side**: When saving a PDF with no user-provided title, the output PDF
  SHALL NOT contain a placeholder title in either the document info (`/Title`)
  or the XMP metadata (`dc:title`). Implemented by post-processing the
  ocrmypdf output with pikepdf when no title was requested.
- **Import side**: When importing a PDF (or other document) whose title is a
  placeholder (`Untitled`, `'Untitled'`, and case-insensitive variants), the
  title SHALL be treated as empty instead of being stored in session metadata.
  This also heals files already saved with the placeholder title.

## Capabilities

### New Capabilities
- `save-pdf-metadata`: When saving a PDF, the metadata written to the output
  matches what the user provided; a missing title results in no title in the
  output, never a placeholder.
- `import-pdf-metadata`: When importing a document, placeholder titles
  (`Untitled`/`'Untitled'` and variants) are normalized to an empty string.

### Modified Capabilities
<!-- None: no existing spec covers PDF save or import metadata behavior. -->

## Impact

- `scantpaper/savethread.py` — `do_save_pdf`: after the ocrmypdf step, strip
  the placeholder title from the output when no title was requested.
- `scantpaper/importthread.py` — `_add_metadata_to_info`: normalize placeholder
  titles read from `pdfinfo`/`djvused`/`tiffinfo` output (single choke point
  for PDF/DjVu/TIFF imports).
- `scantpaper/document.py` — `_extract_metadata` (alternative normalization
  location; decided in design).
- `pyproject.toml` — declare `pikepdf` as a direct dependency (currently only
  transitive via `ocrmypdf`, already imported by the test suite).
- Tests: `scantpaper/tests/test_1111_save_pdf.py`,
  `scantpaper/tests/test_1622_import_multipage_pdf.py`, and the new
  capabilities' delta specs.
