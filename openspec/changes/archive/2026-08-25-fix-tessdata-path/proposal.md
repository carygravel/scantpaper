## Why

Tesseract OCR fails on openSUSE because the tessdata path resolution has two bugs: the fallback search misses SUSE's directory layout, and a missing `return` after `request.error()` allows execution to fall through to the tesseract C library with an invalid path. This is a known SUSE packaging issue (https://forums.opensuse.org/t/tesseract-ocr-wrong-data-directory/164659) where the `tesseract-ocr` binary expects data in `/usr/share/tesseract-ocr/tessdata/` but the traineddata packages install to `/usr/share/tessdata/`.

## What Changes

- Add `return` after `request.error()` in `do_tesseract()` to prevent fall-through to `PyTessBaseAPI` with an invalid path
- Expand the tessdata fallback search to cover SUSE and Fedora/RHEL layouts:
  - `/usr/share/tesseract-ocr/tessdata` (SUSE flat layout, no version directory)
  - `/usr/share/tessdata` (Fedora/RHEL)

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

_(none — pure implementation bug fix, no spec-level behavior change)_

## Impact

- **Code**: `scantpaper/docthread.py` — `do_tesseract()` method only
- **Platforms fixed**: openSUSE Leap/Tumbleweed, Fedora, RHEL, and any distro where tessdata lives outside a versioned subdirectory
- **No API or dependency changes**
