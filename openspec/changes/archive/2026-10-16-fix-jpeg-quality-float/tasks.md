## 1. Regression test first

- [x] 1.1 Add a test in `test_04_page.py` that saving a page as PDF with
      `compression="jpg"` and a float-typed `quality` (e.g. `75.0`) writes
      a valid JPEG stream without raising.
- [x] 1.2 Add a test in `test_04_page.py` that the same float-typed
      `quality` works through the `jb2` codec path (continuous-tone page
      resolving to JPEG).
- [x] 1.3 Extend `test_dialog_save.py` / `test_052_dialog_save.py` to
      assert the `jpeg_quality` property is integer-typed and that a
      spinbutton value round-trips to an integer.

## 2. Encoder normalisation

- [x] 2.1 In `page.py:_encode_jpeg`, coerce `quality` to an integer
      (`round()`) before passing it to `PIL.Image.save`.
- [x] 2.2 Confirm the JPEG branch of `write_image_for_pdf` needs no further
      change and the shared path used by JBIG2 is covered by the new tests.

## 3. Property typing

- [x] 3.1 Change the `jpeg_quality` GObject property in `dialog/save.py`
      from `type=float` to `type=int`, keeping the 1–100 range.
- [x] 3.2 Update the spinbutton read-back so `jpeg_quality` is assigned an
      integer (`int(spinbutton.get_value())`).
- [x] 3.3 Verify `file_menu_mixins.py` assignments of
      `settings["quality"]` now carry an integer for the PDF, TIFF and JPG
      paths.

## 4. Quality gates

- [x] 4.1 Run `pytest` and confirm the full suite (including new tests)
      passes with coverage at or above the existing thresholds.
- [x] 4.2 Run `ruff format` and `ruff check` with no new diagnostics.
- [x] 4.3 Run `ty check .` with no new diagnostics.
- [x] 4.4 If any user-visible change results, update README.md accordingly
      (expected: none, since this restores expected behaviour).
