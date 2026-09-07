## 1. Implementation

- [x] 1.1 In `src/scantpaper/page.py:get_pixbuf_at_scale`, extend the existing
      `mode == "I"` → `"L"` conversion to also convert `mode == "1"` → `"L"`
      and `mode == "P"` → `"RGB"` before the size check, so the
      decimate-then-LANCZOS pipeline anti-aliases bilevel/palette sources.
- [x] 1.2 Remove `"1"` and `"P"` from `_REDUCE_UNSUPPORTED` in
      `src/scantpaper/page.py`, keeping only the 16-bit integer modes.

## 2. Tests

- [x] 2.1 Add a test in `src/scantpaper/tests/test_04_page.py`: a bilevel
      (mode `"1"`) source produces a thumbnail with more than two distinct
      shades (anti-aliased, not a 2-tone collapse).
- [x] 2.2 Add a test that a palette (mode `"P"`) source produces an
      anti-aliased thumbnail with the expected dimensions.
- [x] 2.3 Run the thumbnail-related tests:
      `pytest src/scantpaper/tests/test_04_page.py` and confirm the existing
      reduce+LANCZOS, box-size, and fill-box tests still pass.

## 3. Verification

- [x] 3.1 Run the full test suite `pytest` and confirm coverage thresholds
      still pass.
- [x] 3.2 Run `ruff format` and `ruff check` on changed files and confirm no
      new lint errors.
- [x] 3.3 Regenerate a thumbnail from a 1-bit JBIG2 page and confirm it is
      anti-aliased (multiple shades), matching the `bilevel_gray_first.png`
      reference.
- [x] 3.4 Update the Thumbnails bullet in README.md to mention legible
      anti-aliased bilevel previews.