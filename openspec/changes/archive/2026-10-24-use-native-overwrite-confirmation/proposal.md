# Proposal

## Why

After the GTK3→4 migration, overwriting an existing destination in the Save
flow shows **two** confirmations in a row: GTK4's own native overwrite alert
("A file named … already exists. Do you want to replace it?") **and**
scantpaper's app-level `_confirm_overwrite` dialog ("…Do you want to overwrite
it?"). Before the migration there was exactly one. GTK4 made the native prompt
unconditional in SAVE mode and removed the `do-overwrite-confirmation` property,
so the app-level prompt is now pure duplication that should be dropped.

## What Changes

- **Remove** the app-level `_confirm_overwrite` method and its call in
  `_file_chooser_response_callback` (`src/scantpaper/file_menu_mixins.py`).
- **Rely on GTK4's native overwrite confirmation**, which fires for every
  `_save_file_chooser` output type (PDF, DjVu, TIFF, text, hOCR, Postscript,
  session `.sdb`) and also on the auto-extension re-fire path (verified
  empirically: the native alert is shown before the OK response reaches the
  app, for both the button path and the programmatic `response(OK)` retry).
- **Keep** the suffix-append / `file_exists` re-fire mechanism: it is still
  what makes the chooser return the suffixed filename; confirmation itself is
  now handled by the chooser.
- **Rework** the unit tests that currently assert the app-level prompt's
  behaviour in `test_file_menu_mixins.py` (accept / decline / pdf-djvu prompt
  cases) to match the native-only flow.
- **Update** the `save-overwrite-confirmation` spec so its requirement names
  the native file chooser alert as the confirmation mechanism (see below).

No change to `_save_image` (jpg/png/pnm/gif), which already relies on the
native prompt alone, nor to `_multi_image_filename`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `save-overwrite-confirmation`: change the mechanism by which overwrite
  confirmation is provided. Requirement "Saving to an existing file asks for
  confirmation" is reworded so the confirmation is supplied by the file
  chooser's native prompt (one step, every output type, including the
  auto-appended-extension path) instead of an app-owned dialog. The remaining
  requirements (confirmed session save replaces the destination atomically;
  save failures are reported) are unaffected.

## Impact

- **Code:** `src/scantpaper/file_menu_mixins.py` — delete `_confirm_overwrite`;
  `_file_chooser_response_callback` no longer prompts.
- **Tests:** `src/scantpaper/tests/test_file_menu_mixins.py` — overwrite
  accept / decline / prompt tests for session, PDF and DjVu are reworked or
  removed; no test may still require `_ask_question` in the response callback.
- **Dependencies:** none added or removed.
- **Behaviour:** the user sees exactly one overwrite confirmation (GTK-native
  text and buttons) instead of two; declining still leaves the destination
  untouched and the chooser open.
- **Specs:** delta to `openspec/specs/save-overwrite-confirmation/spec.md`.
