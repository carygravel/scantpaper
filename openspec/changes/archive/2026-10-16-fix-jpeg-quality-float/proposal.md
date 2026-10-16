## Why

Saving a PDF with JPEG or JBIG2 compression fails at runtime with
`ValueError: Invalid quality setting` from Pillow. The configured JPEG
quality is carried through the save path as a `float` (e.g. `75.0`), but
recent Pillow releases (>= 12) reject non-integer qualities, so the save
thread raises and the document is never written. This is a user-visible
regression introduced by a Pillow dependency change, not by recent
scantpaper code.

## What Changes

- Normalise the JPEG quality to an integer at the point where the lossy
  stream is encoded, so a `float` (or integer-valued) quality never reaches
  Pillow's JPEG encoder.
- Make the save dialog's quality property an integer-typed value so the
  source of truth is an `int` from the outset, matching the spinbutton's
  integer range (1–100) and eliminating the float at its origin.
- Add regression coverage that saving with a float-typed quality produces a
  valid JPEG stream instead of raising.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `pdf-image-compression`: the "JPEG quality applied to output" requirement
  gains the invariant that the quality value passed to the JPEG encoder is
  always a valid integer, so lossy saves do not fail when a fractional or
  float-typed quality is supplied.

## Impact

- `src/scantpaper/page.py` — `_encode_jpeg` coerces its quality argument to
  `int` before calling Pillow; the JPEG branch of `write_image_for_pdf`
  benefits automatically.
- `src/scantpaper/dialog/save.py` — the `jpeg_quality` GObject property is
  typed `int` (range unchanged at 1–100).
- `src/scantpaper/file_menu_mixins.py` — the `settings["quality"]` assignment
  already reads from `jpeg_quality`; confirmed to hand an integer onward.
- Tests: `test_04_page.py` (float-quality JPEG encoding) and
  `test_dialog_save.py`/`test_052_dialog_save.py` (property typing and
  spinbutton round-trip).
- No new dependencies. No user-facing UI change beyond restoring the ability
  to save with JPEG/JBIG2.
