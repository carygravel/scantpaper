# Tasks

## 1. Layer Editor Focus Behavior

- [x] 1.1 In `LayerEditor.edit()`, after showing the control bar and loading the
  slice text, focus `self.controls.textview` and select the whole buffer.
  Verify with `pytest src/scantpaper/tests/test_layer.py --no-cov` and a test
  asserting `grab_focus()` and the full-buffer selection.
- [x] 1.2 Ensure `edit(None)` and `clear()` do not request focus. Verify with
  tests that neither path calls `grab_focus()` on the text control.
- [x] 1.3 Extend the layer tests to cover focus and selection for the click,
  navigation, add, duplicate, accept, and annotation paths, and that typing
  replaces the selected text. Verify the focused tests pass.
- [x] 1.4 Update `README.md` to state that focusing a slice puts keyboard focus
  in its text control and selects the text. Verify the wording matches the
  behavior and the Markdown lines stay within 80 characters.

## 2. Integration and Verification

- [x] 2.1 Smoke-test the running application in tabbed and split views: focus a
  slice, press Delete, and verify the text is cleared while the page remains;
  then focus the page list, press Delete, and verify the page is deleted.
- [x] 2.2 Run the full suite with `pytest` and confirm the coverage gate still
  passes, then run `python3 dev/check_test_coverage.py` and confirm the
  unexecuted and partial counts are no worse than the baseline.
- [x] 2.3 Run `ruff format --check`, `ruff check`, and `ty check .` and confirm
  all three are clean.

## Workflow follow-up

- Run `openspec validate --specs --strict --no-interactive`.
- Archive the change after maintainer review, then run
  `openspec validate --archived --no-interactive`.
