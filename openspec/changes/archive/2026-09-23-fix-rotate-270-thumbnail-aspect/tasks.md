## 1. Swap page dimensions for all quarter-turn rotations

- [x] 1.1 Add a regression test: rotating a page by 270 degrees swaps the
      stored width/height and x/y resolution, and the regenerated thumbnail
      has the swapped aspect ratio (mirroring the existing `test_rotate` in
      `tests/test_211_tools.py`).
- [x] 1.2 Add a regression test for the -270 degree case.
- [x] 1.3 Verify the new tests fail against the current code (red), confirming
      they capture the bug.

## 2. Extend the rotation metadata swap

- [x] 2.1 In `do_rotate` (`src/scantpaper/docthread.py`), extend the
      width/height and resolution swap condition from `(-90, 90)` to all
      quarter turns: `(-270, -90, 90, 270)`.
- [x] 2.2 Confirm the 180-degree case still leaves width/height and resolution
      unchanged (existing tests cover this if present; add a scenario if not).

## 3. Verify quality gates

- [x] 3.1 Run the full test suite with coverage (`pytest`): all tests pass and
      coverage stays at or above the configured threshold, with no newly
      uncovered lines.
- [x] 3.2 Run `ruff format` and `ruff check` on the changed files and fix any
      findings.
- [x] 3.3 Run `ty check .` and confirm no diagnostics.
- [x] 3.4 Update README.md changelog-visible notes only if user-visible
      behaviour changes (thumbnail distortion is a bugfix, so note it in
      changelog.md under the unreleased section).