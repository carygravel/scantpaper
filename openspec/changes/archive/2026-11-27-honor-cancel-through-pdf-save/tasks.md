# Tasks

## 1. Regression tests (TDD)

- [x] 1.1 Add a unit test in `src/scantpaper/tests/test_083_basethread.py`
      that runs `handler_wrapper()` with a handler raising `CancelledError`
      and asserts the response queue receives a `CANCELLED` response (not
      `ERROR`) and no error/finished callback fires. Confirm it fails before
      the fix.
- [x] 1.2 Add a unit test in `src/scantpaper/tests/test_savethread.py` that
      drives `SaveThread.do_save_pdf()` with the page-assembly phase mocked to
      succeed and `cancel` set to `True` while the text-layer embed runs, and
      asserts `CancelledError` is raised (so the phase-boundary breakpoint
      stops the save). Confirm it fails before the fix.

## 2. Cancellation through the PDF save

- [x] 2.1 Move `CancelledError` from `scantpaper/importthread.py` to
      `scantpaper/basethread.py` and re-export it from `importthread.py`,
      keeping `from scantpaper.importthread import CancelledError` working.
      Verify the existing `test_check_cancelled` tests still pass.
- [x] 2.2 In `BaseThread.handler_wrapper()`, catch `CancelledError` before the
      generic handler and report it as `request.cancelled()` (still running
      `_request_completed()` and returning `True`), logging at info level
      rather than as a traceback. Verify 1.1 passes and existing base-thread
      error handling tests still pass.
- [x] 2.3 Add `self.check_cancelled()` breakpoints to
      `SaveThread.do_save_pdf()` at the phase boundaries: after
      `_assemble_pdf()`, after `_embed_text_layer()`, after
      `_maybe_convert_to_jbig2()`, and before `do_set_saved()`. Verify 1.2
      passes and the existing `test_save_pdf*` unit tests still pass.
- [x] 2.4 Run the existing end-to-end
      `test_1111_save_pdf.py::test_cancel_save_pdf` and confirm it passes;
      the save is now stopped at a phase boundary instead of completing.

## 3. Integration and quality gates

- [x] 3.1 Add or confirm a changelog entry in `changelog.md` describing that
      cancelling a PDF save now stops the save during the OCR-embed and
      finalize phases and reports cancelled rather than finished or error.
- [x] 3.2 Run the relevant unit tests (`test_083_basethread.py`,
      `test_savethread.py`, `test_1111_save_pdf.py`, `test_basedocument.py`,
      `test_importthread.py`, `test_docthread.py`) and confirm they pass.
- [x] 3.3 Run the full `pytest` suite and confirm the coverage gate passes
      with no newly uncovered or partially covered lines beyond the allowed
      `if TYPE_CHECKING:` imports.
- [x] 3.4 Run `python3 dev/check_test_coverage.py` and confirm the
      uncovered/partial counts are at or below the recorded baseline.
- [x] 3.5 Run `ruff format` and `ruff check` on the changed files and confirm
      both are clean.
- [x] 3.6 Run `ty check .` and confirm there are no diagnostics.
- [x] 3.7 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.
