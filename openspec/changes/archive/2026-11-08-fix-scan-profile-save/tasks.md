# Tasks

## 1. Fix the naming dialog

- [x] 1.1 In `src/scantpaper/dialog/scan.py`, construct the profile naming
      dialog with `title=_("Name of scan profile")` instead of a positional
      title, and verify by clicking Save in a running scan dialog that the
      dialog opens.
- [x] 1.2 Check the other `Gtk.Dialog` call sites for positional arguments with
      `grep -n "Gtk.Dialog(" src/scantpaper` and verify every one passes its
      properties by keyword.

## 2. Regression coverage

- [x] 2.1 In `test_06099_dialog_scan.py`, replace the `Gtk.Dialog` mock in
      `test_save_profile_callback` with a patched `run_dialog` and a real
      dialog; set the name on the real `Gtk.Entry` and assert the dialog title
      is "Name of scan profile" when it is built.
- [x] 2.2 Cover the cancel and empty-name responses against a real dialog and
      verify no profile is created in either case.
- [x] 2.3 In `test_0621_dialog_scan_edit_save.py`, exercise the
      overwrite-confirmation path with a real dialog, verifying the stored
      profile is replaced on confirm and unchanged on cancel.
- [x] 2.4 Assert that saving a profile adds exactly one row with the saved name
      to the profile selector.

## 3. Documentation and quality gates

- [x] 3.1 Document how to save and select a scan profile in `README.md` and
      verify the table-of-contents link resolves.
- [x] 3.2 Add a `changelog.md` entry under 4.0.4 saying that saving a scan
      profile works again.
- [x] 3.3 Run `ruff format`, `ruff check`, `ty check .`, `pytest` and
      `python3 dev/check_test_coverage.py`; verify all pass and coverage stays
      at or above the gate.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
