# Tasks

## 1. Remove the app-level overwrite prompt

- [x] 1.1 Delete `_confirm_overwrite` and its call from
      `_file_chooser_response_callback` in `src/scantpaper/file_menu_mixins.py`,
      leaving the suffix-append / `file_exists` re-fire mechanism exactly as it
      is. Verify: `grep -n "_confirm_overwrite" src` returns nothing and the
      callback flows from `_file_writable` straight to `_save_with_filetype`
      on an OK response.
- [x] 1.2 Rework the overwrite unit tests in
      `src/scantpaper/tests/test_file_menu_mixins.py` to the native-only flow:
      replace `_file_chooser_response_callback_session_overwrite_declined`,
      `_file_chooser_response_callback_session_overwrite_accepted`,
      `_file_chooser_response_callback_pdf_djvu_overwrite_prompts` and
      `_file_chooser_response_callback_overwrite_after_suffix_retry` so an OK
      response saves without consulting `_ask_question` (including after the
      suffix retry re-fires with an existing suffixed file). Verify:
      `pytest src/scantpaper/tests/test_file_menu_mixins.py` passes and the
      reworked tests assert `_ask_question` is not consulted.
- [x] 1.3 Run the full quality gates and confirm coverage is no worse than
      before. Verify: `pytest` passes within the configured coverage
      thresholds, `ruff check .` reports nothing, and `ty check .` reports
      nothing.

## 2. Integration verification

- [x] 2.1 Reproduce the end-to-end flow against the running GTK4 chooser (with
      the Xvfb probe pattern): saving a PDF, DjVu or session over an existing
      destination shows exactly one prompt, the GTK4 native alert with
      `Cancel`/`Replace`. Verify: only the native alert appears on both the
      direct-typing path and the auto-suffix retry path, declining keeps the
      chooser open with the destination untouched, and confirming saves.

## Workflow follow-up

- After implementation and review, archive the change with `openspec archive`
  so `save-overwrite-confirmation` is updated in the main specs.
- Verify the archived result (`openspec show save-overwrite-confirmation
  --type spec`).
