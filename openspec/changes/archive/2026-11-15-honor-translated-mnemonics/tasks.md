# Tasks

## 1. Rendered-state regression tests (TDD)

- [x] 1.1 Add a test that loads the main window and asserts every button
      built from `app.ui` with a non-empty label has its mnemonic enabled
      (`get_use_underline()` is true); confirm it fails before the fix.
- [x] 1.2 Add a test that `labelled_icon_button()` given `_Löschen` builds
      a button whose label has the mnemonic enabled and whose accessible
      label is `Löschen`; confirm it fails before the fix.
- [x] 1.3 Add tests for the marker-stripping helper covering a leading
      marker, a mid-string marker, a doubled marker (`__` yields one
      literal `_`) and a marker-free label returned unchanged.

## 2. Mnemonic rendering

- [x] 2.1 Add a helper in `helpers.py` that enables `use-underline` on
      every `Gtk.Button` with a label among the objects returned by
      `Gtk.Builder.get_objects()`, and call it from `ApplicationWindow`
      after `add_from_file()`; verify 1.1 passes.
- [x] 2.2 Add the marker-stripping helper in `helpers.py` following the
      parsing verified in `design.md`; verify 1.3 passes.
- [x] 2.3 Build the label in `labelled_icon_button()` with
      `Gtk.Label.new_with_mnemonic()` and set the accessible label from
      the stripped text; verify 1.2 passes.

## 3. Template references

- [x] 3.1 Add a test in `src/scantpaper/tests/test_po_files.py` that a
      string occurring in both a Python module and a GtkBuilder `.ui` file
      lists both source references in the generated template, and that the
      msgid set is otherwise unchanged; confirm it fails with the current
      merge.
- [x] 3.2 Merge the intermediate templates without `--use-first` in
      `dev/generate_pot.py`; verify 3.1 passes and
      `PYTHONPATH=src python3 dev/check_po.py` still reports zero errors.

## 4. Documentation

- [x] 4.1 Add a changelog entry under 4.0.5 noting that a translation
      which marks a keyboard mnemonic now shows it as an accelerator
      rather than a literal underscore; verify the entry names the
      affected buttons (view toolbars and the scan-profile row) and states
      that no translated text changes.
- [x] 4.2 Add a sentence to the Translations section of `README.md`
      telling translators that `_` marks a keyboard mnemonic and `__` is
      a literal underscore; verify it sits beside the existing note on
      fuzzy entries.

## 5. Integration and quality gates

- [x] 5.1 Run the full `pytest` suite and confirm the coverage gate passes.
- [x] 5.2 Run `python3 dev/check_test_coverage.py` and confirm the counts
      are at or below the recorded baseline.
- [x] 5.3 Run `ruff format` and `ruff check` and confirm both are clean.
- [x] 5.4 Run `ty check .` and confirm there are no diagnostics.
- [x] 5.5 Run `openspec validate --specs --strict --no-interactive` and
      `openspec validate --archived --no-interactive` and confirm both pass.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
- Verify the archived result.
