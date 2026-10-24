# Design

## Context

See proposal.md - Why for the motivation. The relevant mechanics today:

- `_save_file_chooser` (`file_menu_mixins.py`) builds a SAVE-mode
  `Gtk.FileChooserDialog` that connects `_file_chooser_response_callback` to
  `response`. On OK, the callback appends a missing extension and, when the
  suffixed file exists, `file_exists` sets the file and re-fires
  `Gtk.ResponseType.OK` from an idle callback (the "auto-suffix retry").
- The callback then calls the app-owned `_confirm_overwrite`, which uses the
  shared `_ask_question` dialog helper.
- GTK4 (verified against gtkfilechooserwidget.c, 4.24, and reproduced on a
  live display): the SAVE-mode file chooser now **always** presents its own
  overwrite alert (`A file named "%s" already exists. Do you want to replace
  it?`, buttons `_Cancel`/`_Replace`) before emitting an accept response. The
  GTK3 `do-overwrite-confirmation` property was removed from the GTK4 API, so
  this prompt cannot be disabled. It fires both on the button path and on the
  programmatic `response(OK)` re-fire used by `file_exists`.

## Goals / Non-Goals

**Goals:**

- Exactly one overwrite confirmation per save, provided by GTK4's native alert.
- Preserve the confirmed behaviour: nothing is written before confirmation,
  declining (or the native Cancel) leaves the destination untouched and the
  chooser open.

**Non-Goals:**

- Porting `_save_file_chooser` to the new `Gtk.FileDialog` API; the chooser
  stays a `Gtk.FileChooserDialog`.
- Touching `_save_image` or `_multi_image_filename` (image saves already rely
  on the native prompt alone).
- Restructuring the suffix-append / `file_exists` re-fire mechanism.
- Changing the atomic session-replace logic (D2 of the archived
  fix-session-overwrite change) or the save failure reporting.

## Decisions

### D1: Rely on GTK4's native overwrite confirmation; delete `_confirm_overwrite`

**Choice:** remove `_confirm_overwrite` and its call in
`_file_chooser_response_callback`. The GTK4 chooser's native alert becomes the
single, sole confirmation for every `_save_file_chooser` output type
(session, PDF, DjVu, TIFF, text, hOCR, Postscript), including the auto-suffix
retry.

**Why:**

- The native prompt is now unconditional in SAVE mode and cannot be disabled,
  so an app-level prompt is pure duplication (the current two-dialog bug).
- Verified empirically that the native alert fires for both the normal accept
  path and the `file_exists` programmatic re-fire, so removing the app-level
  check does not reopen the overwrite-without-confirmation gap the
  app-level prompt was introduced to close.
- GTK handles the confirm/decline semantics: `_Cancel`/`_Replace`; declining
  emits no accept response, so the callback never runs and the chooser stays
  open - matching the spec scenarios.

**Alternatives considered:**

- *Keep `_confirm_overwrite` and suppress the native alert* - not possible:
  the disabling property does not exist in GTK4 and there is no supported
  knob on `Gtk.FileChooserDialog`.
- *Keep both* - the status quo: two sequential, visually inconsistent
  prompts (native "Replace?" then app "Overwrite?" with the full path).
- *Replace the chooser with Gtk.FileDialog* - out of scope; the new API would
  change the whole save dialog interaction model and translations.

### D2: Keep the suffix-append / `file_exists` re-fire as-is

**Choice:** leave `_normalize_filetype_suffix`, the extension append, and
`file_exists` unchanged after dropping `_confirm_overwrite`.

**Why:**

- The re-fire exists to make the chooser return the full suffixed filename
  (`chooser_path()` then yields `foo.pdf`), which the save paths depend on.
- Confirmation is no longer that helper's job: GTK's native alert fires on
  the re-fired response too (verified), so no confirmation gap appears.

### D3: Update the unit tests to the native-only flow

**Choice:** remove or rework the tests in `test_file_menu_mixins.py` that
assert `_ask_question` inside the response callback
(`test_file_chooser_response_callback_*_overwrite_*`,
`test_file_chooser_response_callback_pdf_djvu_overwrite_prompts`).

**Why:**

- Those tests mock `_confirm_overwrite`/`_ask_question`, a code path being
  deleted. The new confirmation lives inside GTK and is not unit-testable
  with the mocked bindings.
- The observable guarantee (one prompt before write, decline leaves file
  untouched) is captured by the spec scenarios; where useful, a mock-based
  test can still assert that the callback no longer consults `_ask_question`
  and proceeds straight to the save when OK arrives.

## Risks / Trade-offs

- [Confirmation dialog styling and text no longer match the app's `_ask_question`
  dialogs (e.g. "replace" wording, different button labels)] →
  It is the stock GTK4 dialog, localized by GTK's own catalogs; consistency
  with other apps is a benefit, and the app-level dialog only doubled the
  prompts.
- [A future GTK/platform change could alter native prompt behaviour] →
  The widget-based `Gtk.FileChooserDialog` (not the portal-backed
  `Gtk.FileChooserNative`) is used, so behaviour is tied to GTK itself;
  regression would surface through the spec scenarios' observables.
- [Deleting `_confirm_overwrite` removes a unit-testable policy point] →
  Accepted; GTK now owns the policy. Tests are reworked rather than kept
  against dead code.
- [App prompts suppressed for exotic cases (e.g. an existing directory as
  destination)] → The old `_confirm_overwrite` used `Path.is_file()` and never
  guarded directories either, so behaviour is unchanged; a save over a
  directory still surfaces as a save error dialog.

## Migration Plan

Behaviour-only change; no data, config, or file-format migration. Rollback is
restoring `_confirm_overwrite` and its call site. Sequencing: code change and
test rework together, README only if user-visible text is affected (it is not -
native dialog text belongs to GTK).

## Open Questions

None - the unknowns relevant to the approach (native prompt on both accept
paths) were resolved empirically; anything left (exact GTK wording) is
implementation detail that cannot change the spec, design, or tasks.
