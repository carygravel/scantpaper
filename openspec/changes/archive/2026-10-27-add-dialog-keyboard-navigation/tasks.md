# Tasks

## 1. OCR advanced parameters field

- [x] 1.1 In `postprocess_controls.py::_add_advanced_options`, make the
      advanced Tesseract engine parameters text view release the Tab key
      (stop it accepting Tab); verify a widget-level test in
      `test_postprocess_controls.py` asserts the field does not accept Tab.

## 2. Text-layer editing control

- [x] 2.1 In `layer.py`, keep a reference to the text-layer editing text view
      and make it release the Tab key; verify a widget-level test asserts the
      editing text view does not accept Tab.

## 3. Documentation and verification

- [x] 3.1 Document the keyboard-navigation behaviour (Tab moves focus out of
      dialog text views, so OK/Close stay reachable; Ctrl+Tab /
      Ctrl+Shift+Tab also move focus) in `README.md`; verify the note is
      present and reads correctly.
- [x] 3.2 Verify in a running instance that Tab and Shift+Tab move focus out of
      the OCR advanced field and the text-layer editor, and that Ctrl+Tab /
      Ctrl+Shift+Tab are not swallowed.
- [x] 3.3 Run `pytest` and verify all tests pass with the uncovered and
      partially-covered line counts no worse than before.
- [x] 3.4 Run `ruff format --check .`, `ruff check .` and `ty check .` and
      verify all report no problems.
