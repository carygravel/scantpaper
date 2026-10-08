## 1. Failing tests for overwrite confirmation

- [x] 1.1 Test: confirming an existing session (`.sdb`) destination prompts via
      `_ask_question`, and declining leaves the chooser open with no save
      (extend `tests/test_file_menu_mixins.py` around
      `test_file_chooser_response_callback_session`)
- [x] 1.2 Test: confirming an existing destination prompts for pdf and djvu
      too (regression coverage for removing the native
      `set_do_overwrite_confirmation` branch)
- [x] 1.3 Test: the auto-suffixed retry path (name typed without extension,
      suffixed file exists) reaches the confirmation before saving
- [x] 1.4 Test: `_save_file_chooser` sets up the chooser the same way for
      every output type (no pdf/djvu-only branch)

## 2. Failing tests for session save replacement

- [x] 2.1 Test: `docthread.save_as` overwrites an existing non-empty session
      file with a real temp database (no mocked `execute`)
- [x] 2.2 Test: `save_as` failure leaves the previous destination file
      byte-for-byte intact and removes the temp file
- [x] 2.3 Test: `save_as` succeeds for a destination path containing a single
      quote
- [x] 2.4 Test: a failure inside the response callback shows
      `_show_message_dialog` and still dismisses the chooser (no escaped
      exception)

## 3. Implementation

- [x] 3.1 Add the app-level existence check + `_ask_question` confirmation to
      `_file_chooser_response_callback`; remove
      `set_do_overwrite_confirmation(True)` from `_save_file_chooser`
- [x] 3.2 Rework `docthread.save_as` to `VACUUM INTO ?` a temp file in the
      destination directory, `os.replace` it onto the destination, and clean
      up the temp file in `finally`
- [x] 3.3 Wrap the save call in the response callback with
      `try/except` → log + `_show_message_dialog`, then destroy the dialog

## 4. Verification and docs

- [x] 4.1 `pytest` green with no drop in coverage (no new uncovered lines
      outside `TYPE_CHECKING`)
- [x] 4.2 `ruff format` + `ruff check` clean; `ty check .` clean
- [x] 4.3 Manual check: overwrite a saved session (decline, then confirm) and
      confirm the previous file survives a forced failure
- [x] 4.4 Document the overwrite-confirmation behaviour in README.md if user-
      visible behaviour is described there
