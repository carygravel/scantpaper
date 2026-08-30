## 1. Relocate the truncated-PNM coverage

- [x] 1.1 Add a truncated-PNM import test to `scantpaper/tests/test_1631_import_images.py`, alongside `test_import_ppm`: build the `rose:` PPM, truncate it to 1000 bytes (as `test_101_document.py:861-872` did), import it via `slist.import_files(paths=[...])` using the `temp_db`/`temp_ppm`/`get_page_sync` fixtures, and assert the resulting page is full size (`page.image_object.size == (70, 46)` and mode `"RGB"`). Verify the new test passes: `python3 -m pytest scantpaper/tests/test_1631_import_images.py -q -p no:cacheprovider`.
- [x] 1.2 Remove `test_import_scan` from `scantpaper/tests/test_101_document.py` (lines ~852-914) including its FIXME comment, and drop any `temp_pnm`/`temp_ppm` fixture usages that become unused there. Verify `test_101_document.py` still imports/collects cleanly: `python3 -m pytest scantpaper/tests/test_101_document.py -q -p no:cacheprovider`.

## 2. Verification & quality

- [x] 2.1 Run the full suite and confirm no test loss beyond the relocated one: `python3 -m pytest scantpaper/tests -q -p no:cacheprovider` — count of passed tests unchanged (relocated test counts 1 for 1).
- [x] 2.2 Confirm pylint no longer reports the FIXME: run `pylint --persistent=no scantpaper/tests/test_101_document.py scantpaper/tests/test_1631_import_images.py` and verify W0511 is gone and warning count is same or lower than baseline.
- [x] 2.3 Coverage: `python3 -m coverage json` — line/branch coverage of `page.py` (the `LOAD_TRUNCATED_IMAGES` path) must not decrease relative to baseline.
- [x] 2.4 Format changed files with `black` (`scantpaper/tests/test_101_document.py`, `scantpaper/tests/test_1631_import_images.py`).