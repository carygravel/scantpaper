## 1. Batch handling in the worker thread

- [ ] 1.1 Extend `savethread.user_defined()` / `do_user_defined()` to accept an
      options dict carrying a list of pages (e.g. `pages` mapping page id to
      page) and dispatch to a batch branch when present; keep the existing
      single-page path byte-for-byte unchanged.
- [ ] 1.2 Batch working-file setup: for each page in the batch create a temp
      working copy of the page image (reusing the existing copy step from the
      no-`%o` single-page path), record a byte digest of the file, and keep a
      `page_id → working_path` mapping so copy-back is deterministic.
- [ ] 1.3 Batch command substitution: substitute `%i` with all working paths,
      space-joined; if the command contains `%o`, raise/return a single batch
      error naming the tool and run nothing.
- [ ] 1.4 Run the single batch invocation through `exec_command_run` with a
      pidfile and `check_cancelled()`, exactly like the single-page path, so a
      cancelled run terminates the spawned process group and performs no
      copy-back.
- [ ] 1.5 Batch copy-back: after the process exits, replace only those pages
      whose working-file digest changed, building the new `Page` from the old
      page's resolution and text layer (same construction as the single-page
      path) and emitting the same `{"type": "page", "row", "replace"}` data
      response per replaced page; skip unchanged working files entirely.

## 2. Document and base-document plumbing

- [ ] 2.1 Add a page-list-aware `user_defined()` to `document.py` (and the
      `basedocument.py` wrapper) that forwards a list of pages for batch and
      still supports the current single-page call signature used by the
      per-page loop.
- [ ] 2.2 Ensure `data_callback()` (`basedocument.py`) handles multiple
      per-page `replace` responses from one batch without thrashing the image
      view (coalesced display, consistent with the async-display-image spec).

## 3. Dialog and user-facing behaviour

- [ ] 3.1 Add a "Process selected pages at once" checkbox to
      `user_defined_dialog()` in `tools_menu_mixins.py`, defaulting to
      unchecked.
- [ ] 3.2 In the dialog's apply callback, branch: batch mode makes one
      `slist.user_defined(pages=[...], command=...)` call; otherwise keep the
      existing per-page loop. Pass the chosen tool through unchanged.
- [ ] 3.3 Reject batch mode up front when the selected command contains `%o`:
      show an error dialog and do not start the tool (mirrors the worker-side
      check).
- [ ] 3.4 Add the user-facing batch result/error messages: an error-string
      naming the tool when the invocation fails, and a "no pages modified"
      message that hints the tool may have handed off to an already-running
      instance (GIMP single-instance behaviour).

## 4. Progress and cancellation

- [ ] 4.1 Verify a batch is reported as a single job ("Process 1 of 1
      (user_defined)") through the queued/started/running/finished lifecycle
      and that the progress bar cancels correctly (connect
      `post_process_progress` as today).
- [ ] 4.2 Add a test asserting that cancelling a batch terminates the spawned
      process and results in zero pages replaced.

## 5. Tests

- [ ] 5.1 Extend `test_371_user_defined.py` with a batch scenario using a CLI
      tool that accepts multiple inputs and edits in place (e.g.
      `mogrify -negate %i`): all pages' files are passed to one invocation and
      all edited pages are replaced.
- [ ] 5.2 Test that a mixed batch replaces only modified working files and
      leaves unmodified files' pages untouched, preserving page order.
- [ ] 5.3 Test that batch mode refuses `%o` both in the dialog and in
      `do_user_defined`, with no tool started.
- [ ] 5.4 Test that a failing batch produces a single error and replaces no
      pages (extend `test_savethread.py` `test_user_defined*` cases).
- [ ] 5.5 Test the "no pages modified" outcome when the batch exits 0 and no
      working file changed.
- [ ] 5.6 Test that batch-replaced pages keep resolution and text layer and
      mark the document unsaved (mirror existing UDT assertions).
- [ ] 5.7 Extend `test_tool_menu_mixins.py` to cover the new checkbox: batch
      mode sends one page-list request, per-page mode still loops.
- [ ] 5.8 Keep the existing single-page UDT tests green unchanged (regression
      guard for the default path).

## 6. Quality gates and docs

- [ ] 6.1 Run `ruff format` and `ruff check` on changed files and fix any
      issues; ensure coverage thresholds in `pyproject.toml` are met.
- [ ] 6.2 Update README.md to document batch mode for user-defined tools
      (checkbox behaviour, `%o` restriction).
- [ ] 6.3 Regenerate the translation template with
      `PYTHONPATH=src python3 dev/generate_pot.py` for any new interface
      strings (checkbox label, batch messages).