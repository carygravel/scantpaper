## Why

`test_import_scan` in `test_101_document.py:852` carries a FIXME (pylint W0511):
"not sure we need this anymore, now we are passed Image objects around". The
premise is correct *for scans*: the only production caller of `import_scan`
passes `image_object` (`scan_menu_item_mixins.py:393`), so a scanner writing a
truncated PNM file — the original motivation for the test — is no longer
possible on the scan path. But the behavior the test guards is not dead: it is
the PIL truncation tolerance enabled by `ImageFile.LOAD_TRUNCATED_IMAGES = True`
(`page.py:19`), which still matters for `import_files`, the path that reads raw
files from disk via `Page(filename=...)` (`importthread.py:287-339`). The
coverage needs to move to where the risk actually lives, and the FIXME goes
away.

## What Changes

- **Remove the truncated-PNM padding coverage from `test_import_scan`**
  (`test_101_document.py:852-914`). The test's only assertions concern the
  truncated-file padding behavior, which is no longer scan-shaped. The
  `import_scan` API itself remains covered elsewhere
  (`test_51_process_chain.py`, `test_pagecontrols.py:102`,
  `test_0601_dialog_scan.py`), so nothing about normal scan import is lost.
- **Add the equivalent truncated-file test to `test_1631_import_images.py`**
  (the existing home for PPM import coverage, next to `test_import_ppm`), using
  `import_files` to import a deliberately truncated PNM and asserting it still
  becomes a full-size page. This keeps a regression guard on
  `LOAD_TRUNCATED_IMAGES` where truncated files can actually occur.
- **Delete the FIXME comment.** Resort to a plain explanatory comment if it adds
  context in its new home.

This is a pure test reorganization: no runtime behavior changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No spec-level behavior changes (import/scan behavior is unchanged; tests
are relocated). This change opts out of specs via `skip_specs: true`.

## Impact

- `scantpaper/tests/test_101_document.py` — `test_import_scan` removed (and the
  `temp_pnm`/`temp_ppm` fixture usage there, if it becomes unused).
- `scantpaper/tests/test_1631_import_images.py` — truncated-PNM import test
  added.
- No production code, no dependencies, no DB schema change. Pylint W0511 for
  this FIXME disappears; test coverage of truncation tolerance is preserved
  across a different entry point.