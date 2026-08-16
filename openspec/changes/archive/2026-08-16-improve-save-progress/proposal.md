## Why

Saving a document as PDF shows no progress during the slowest phases: the per-page image-write loop (which does the heavy PNG encoding) reports nothing, and the visible "Saving page i of n" progress only runs *after* img2pdf has already finished, in the fast hocr-write loop. For large documents (e.g. 250 archive pages) the progress bar sits frozen at "Setting up PDF" for minutes, then reports work that has already been done.

## What Changes

- During PDF save, report per-page progress (fraction + message) from the image-write loop, where the actual work happens — matching the pattern already used by the DjVu and TIFF save paths.
- Show a "Writing PDF…" message while `img2pdf.convert()` runs, so the user sees that conversion is in progress rather than a frozen bar.
- Remove the mislocated per-page progress reporting from the hocr text-write loop that runs after img2pdf.

## Capabilities

### New Capabilities
- `save-progress-reporting`: Governs how the post-process progress bar reports progress while a PDF is being saved — which save stages report per-page progress and which report stage-level messages.

### Modified Capabilities
<!-- None: the existing progress-bar-lifecycle capability is scoped to the scan progress bar and is unaffected by this change. -->

## Impact

- `scantpaper/savethread.py` — `do_save_pdf()` only.
- No dependency changes; no schema/DB changes.
- Tests: `scantpaper/tests/test_savethread.py` progress-related tests may need updating (`test_save_pdf_with_progress_hooks`, `test_save_pdf_progress_updates_during_ocr`).
- i18n: reuses the already-translated "Writing page %i of %i" string from the DjVu save path; the "Writing PDF…" string is new and needs the translation template regenerated for upload to Rosetta.
