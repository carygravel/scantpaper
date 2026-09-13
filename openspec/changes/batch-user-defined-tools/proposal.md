## Why

Applying a user-defined tool (UDT) such as GIMP to several selected pages runs
the tool once per page, strictly serially. For long-lived GUI tools this forces
the user to open, edit, save, and close the application once per image (for 5
images: open and close GIMP 5 times). Users expect the tool to open all
selected images at once so editing one document's pages is a single workflow.

## What Changes

- Add a batch mode for user-defined tools: when enabled, all selected pages are
  passed to a single invocation of the tool, so e.g. `gimp %i` opens all chosen
  images at the same time.
- Add a user control in the User-defined tools dialog (a checkbox) to turn batch
  mode on per use.
- After the single batch invocation exits, each input file that was modified is
  read back and used to replace its corresponding page, preserving page order.
  Unmodified inputs leave their page untouched.
- Error handling: if the batch tool exits nonzero or no output is produced,
  report a single error for the batch rather than per-page errors.
- Progress reporting and cancellation continue to work for a batch treated as a
  single job.

Explicitly out of scope (V1):

- Tools that emit a single multi-page output file (`%o` writing a PDF/TIFF
  collecting many inputs) and tools that reorder, add, or merge pages.
- Fixing the latent single-instance race where a GUI tool (e.g. GIMP) is already
  running when the batch is launched; that behavior is unchanged and documented.

## Capabilities

### New Capabilities

- `user-defined-tools`: Running user-defined commands on pages, including the
  interactive dialog, per-page mode, and the new batch mode where all selected
  pages are passed to one invocation.

### Modified Capabilities

<!-- None: there is no existing spec covering user-defined tools. -->

## Impact

- `src/scantpaper/tools_menu_mixins.py`: `user_defined_dialog()` — add the
  batch checkbox and pass the batch flag through.
- `src/scantpaper/docthread.py` / `src/scantpaper/savethread.py`:
  `do_user_defined()` — support a list of pages/inputs in one request:
  - Substitute `%i` with all input paths.
  - Copy back each modified input to its page.
  - Keep the `%o` single-output path working for per-page tools.
- `src/scantpaper/basedocument.py`: `user_defined()` plumbing to accept a
  list of pages.
- `src/scantpaper/document.py`: `user_defined()` wrapper passes a page list.
- `src/scantpaper/helpers.py`: reuse `exec_command_run` unchanged; batch still
  blocks on a single process.
- Progress/status: `src/scantpaper/progress.py` usage in
  `tools_menu_mixins.py` (`post_process_progress`) — batch treated as one job.
- Config: no new persisted settings; batch is a per-use dialog choice.
- No new dependencies. Tests in `src/scantpaper/tests/` (e.g.
  `test_371_user_defined.py`, `test_savethread.py`, `test_file_menu_mixins.py`).