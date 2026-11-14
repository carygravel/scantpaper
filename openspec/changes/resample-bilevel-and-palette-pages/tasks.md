# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add a test in `src/scantpaper/tests/test_04_page.py` that saves a
      bilevel page with downsampling and asserts the embedded image is
      bilevel at the target size.
- [x] 1.2 Add a parameterised test that saves a palette page with and
      without transparency, asserting the resampled image is RGB or RGBA at
      the target size.
- [x] 1.3 Confirm the bilevel test fails on Ubuntu 26.10 before the fix.

## 2. Resize helper

- [x] 2.1 Add `_resize_image()` to `src/scantpaper/page.py`, resampling
      bilevel pages through grayscale and resampling palette pages in true
      colours.
- [x] 2.2 Use the helper for the downsampling branch of
      `write_image_for_pdf()`.
- [x] 2.3 Use the helper in `_equalize_resolution()`.

## 3. Documentation

- [x] 3.1 Add a changelog entry under 4.0.4.
- [x] 3.2 Record the affected Pillow versions (Ubuntu's 12.1 on 26.04 and
      12.3 on 26.10), the bad Ubuntu backport of an upstream Pillow commit
      that causes them to differ from the PyPI builds, and the end-of-life
      removal condition in the `_resize_image()` docstring, the design and
      the changelog.

## 4. Integration and quality gates

- [ ] 4.1 Run the full `pytest` suite and confirm the coverage gate passes.
- [ ] 4.2 Run `python3 dev/check_test_coverage.py` and confirm the counts are
      at or below the recorded baseline.
- [ ] 4.3 Run `ruff format` and `ruff check` and confirm both are clean.
- [ ] 4.4 Run `ty check .` and confirm there are no diagnostics.
- [ ] 4.5 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
