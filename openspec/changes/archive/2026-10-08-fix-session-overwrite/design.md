## Context

See proposal.md for the problem statement. The relevant mechanics:

- `_save_file_chooser` (`file_menu_mixins.py:460`) builds the SAVE chooser
  asynchronously (`connect("response", ...)`, no `run()`), and only sets
  `set_do_overwrite_confirmation(True)` inside the `image type in ["pdf",
  "djvu"]` branch (`:503-516`).
- `_file_chooser_response_callback` (`:570`) appends a missing suffix, and if
  the suffixed file exists, `file_exists` (`:66`) sets the name and re-emits
  `Gtk.ResponseType.OK` from an idle callback — a programmatic response that
  never passes through the file chooser widget's own OK handling.
- Session save is the only save path with no async error callback:
  `_save_with_filetype` → `slist.save_session` → `docthread.save_as`, which
  runs `VACUUM INTO '<path>'` (`docthread.py:330`). `VACUUM INTO` refuses to
  write over an existing non-empty database (`OperationalError: output file
  already exists`), and the f-string breaks on paths containing `'`.
  The exception escapes the GTK callback, so `dialog.destroy()` never runs and
  no message is shown.

Verified on this machine (sqlite 3.53.4): `VACUUM INTO` succeeds only for a
non-existent or empty destination; parameter binding (`VACUUM INTO ?`) works and
avoids the quoting bug.

## Goals / Non-Goals

**Goals:**

- One confirmation step for overwriting an existing destination, for every
  output type in the `_save_file_chooser` flow, including the auto-suffixed
  retry path.
- Session save that can genuinely replace a previous file, atomically.
- Session save failures reported through the existing error-dialog mechanism,
  with deterministic chooser lifecycle.

**Non-Goals:**

- Redesigning the suffix-append / `file_exists` idle re-fire mechanism; it stays
  as the way the suffixed name is retried.
- Changing `_save_image` (jpg/png/…), which already uses the synchronous
  `run()` chooser with native overwrite confirmation (`:821`), or the
  multi-page "This operation would overwrite %s" template check (`:857`).
- Moving session save onto the worker thread / adding progress reporting for
  it; `save_as` keeps running where it runs today.
- Open/restore flows (`open_session`) and session file format changes.

## Decisions

### D1: App-level confirmation in the response callback, not GTK's native flag

**Choice:** perform the existence check and confirmation inside
`_file_chooser_response_callback` using the existing `_ask_question` helper
(the same pattern `_pages_saved` uses, `file_menu_mixins.py:996`), and drop the
`set_do_overwrite_confirmation(True)` call from `_save_file_chooser`.

**Why:**

- A single code path covers both cases: a normal OK click *and* the programmatic
  `response(OK)` re-fire from `file_exists`. GTK's native confirmation only
  fires from the file chooser widget's own OK handling, so the re-fired
  response would silently bypass it — the exact "does nothing / silently
  overwrites" gap we are closing.
- It is uniform for all output types instead of the current pdf/djvu-only
  flag.
- It is unit-testable in a suite that mocks `Gtk` heavily; the flag's effect
  lives inside GTK and is invisible to those tests.

**Alternatives considered:**

- *Enable `set_do_overwrite_confirmation(True)` for all types* — one line, stock
  dialog, but leaves the re-fire path unconfirmed and untestable, and would
  double-prompt alongside an app-level check.
- *Keep native for pdf/djvu, app-level for the rest* — two mechanisms, two
  dialog styles, and the pdf/djvu re-fire path still bypasses confirmation.
- *Emit `response(OK)` only after our own check in `file_exists`* — keeps the
  helper in charge of policy but splits confirmation across two places.

Declining leaves the chooser open (early `return` before `dialog.destroy()`),
which is what the spec requires and what the existing `file_exists` path
already does.

### D2: Overwrite via temp file in the destination directory + `os.replace`

**Choice:** `save_as` writes `VACUUM INTO ?` with a temporary path in the same
directory as the destination, then `os.replace(tmp, destination)`; the temp
file is removed in a `finally` if anything fails.

**Why:**

- `VACUUM INTO` cannot target an existing non-empty database at all, so the
  target must be a fresh file; `os.replace` then swaps it in atomically.
- Same-directory temp guarantees the same filesystem, so `os.replace` is atomic
  on POSIX (and on Windows).
- If `VACUUM` fails at any point, the user's previous session file has not been
  touched — non-negotiable for a file the user chose to overwrite.
- Parameter binding fixes the `'`-in-path bug for free.

**Alternatives considered:**

- *Unlink destination first, then `VACUUM INTO`* — simplest, but a failed save
  destroys the previous file (violates the spec's failure scenario).
- *`VACUUM INTO` straight to the destination* — fails on existing files, the
  current bug.
- *SQLite backup API (`Connection.backup`)* — would overwrite an existing
  database in place, but adds a second connection/lifecycle to manage on the
  main thread and still needs care for partial failure; temp + replace is
  smaller and safer.

### D3: Catch failures at the chooser response boundary

**Choice:** wrap the `_save_with_filetype` call in the response callback with
`try/except`, log the exception, show it via `_show_message_dialog` (the
existing error-dialog helper), then fall through to `dialog.destroy()`.

**Why:**

- It is the one place that owns the chooser's lifecycle, so "report, then
  dismiss" needs no changes elsewhere.
- The other output types already have their own `error_callback` plumbing
  inside the async save machinery; catching here only adds a safety net for
  what currently escapes (the session path) without restructuring those flows.
- Keeps session save synchronous as it is today (Non-Goal), while still meeting
  the reporting requirement.

**Alternative considered:** giving `save_session` an `error_callback` to match
the async save machinery — the right long-term shape, but it changes the
document/thread contract for one call site; out of scope here.

## Risks / Trade-offs

- [Confirmation dialog differs from GTK's stock overwrite dialog] → Same
  information (proceed / pick another name), reuses the app's established
  `_ask_question` pattern and translations; acceptable for consistency and
  testability.
- [Nested modal (`_ask_question` runs a recursive main loop) inside the
  `response` handler] → Precedent already exists in `_pages_saved`; the handler
  does no other work while the modal is up.
- [Removing the native flag for pdf/djvu could regress their confirmation] →
  The app-level check now covers them explicitly; add a test for pdf with an
  existing destination.
- [Temp file left behind if the app dies mid-save] → Temp lives next to the
  destination with an obvious name and is removed in `finally`; a stray file is
  preferable to a corrupted session.
- [Session save still runs on the main thread and can block the UI on large
  documents] → Pre-existing behaviour, explicitly out of scope.
- [Tests currently mock `save_session` / `save_as`, so nothing in the suite
  would have caught this] → Tasks include replacing the mock-only assertions
  with a real end-to-end overwrite test against a temp database.

## Migration Plan

Behaviour-only change; no data, config, or file-format migration. Old session
files remain readable; no rollback concerns beyond reverting the commit.

## Open Questions

None — the spec's requirements are fully determined by Decisions D1–D3.
