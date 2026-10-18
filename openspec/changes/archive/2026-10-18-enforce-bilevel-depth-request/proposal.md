## Why

When a scan profile requests a colour depth of 1 bit, some SANE backends
still deliver 8-bit frames - typically when a hardware compression option
such as JPEG is active. scantpaper imports such frames as grayscale
without checking them against the requested depth, so saving with
"Automatic" PDF compression embeds them as JPEG instead of Group 4 or
JBIG2. The user's explicit 1-bit request is silently lost, and the
surprise only surfaces as an unexpectedly large PDF.

## What Changes

- Scan import compares the requested colour depth with the frame the
  device actually delivered. When 1-bit depth was requested and the
  delivered frame carries more depth, the page SHALL be converted to
  1-bit at import time, reusing the threshold tool's colour-aware
  ink-strength semantics and the configured threshold value.
- The user SHALL be informed when this happens - non-blocking, so a
  multi-page batch does not produce repeated dialogs.
- Frames the device delivered as 1-bit, and frames scanned without a
  1-bit depth request, SHALL be imported unconverted.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sane-page-acquisition`: new requirement that a requested colour
  depth is honoured at acquisition - delivered frames deeper than
  requested are converted (and reported) instead of being imported
  as-is.

## Impact

- `src/scantpaper/dialog/sane.py`: detect the mismatch in
  `new_page_callback` (has both the delivered image and the current
  scan profile) and pass a flag along the "new-scan" signal.
- `src/scantpaper/scan_menu_item_mixins.py`: map the flag to an import
  option in `_new_scan_callback`.
- `src/scantpaper/document.py` and `src/scantpaper/docthread.py`: run
  the conversion as the first post-process step of the scan import,
  reusing the existing `threshold` handler.
- README and changelog: document the behaviour.
- No dependency or configuration-format changes; the existing
  "threshold tool" value steers the conversion.
