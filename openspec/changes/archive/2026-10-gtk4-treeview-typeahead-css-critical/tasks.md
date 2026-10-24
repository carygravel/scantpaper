# Tasks

## 1. Core Implementation

- [x] 1.1 Add `self.set_enable_search(False)` in `SimpleList.__init__`
  (src/scantpaper/simplelist.py), immediately after `super().__init__()`,
  with a comment citing the upstream GTK bug
  (`gtk_tree_view_ensure_interactive_directory`, `gtk_css_node_insert_after`,
  present through gtk-4-24) and noting that no search column is ever set, so
  typeahead has no user value. Verify: `ruff check --no-fix` and
  `ruff format --check` on `src/scantpaper/simplelist.py` pass, and
  `ty check .` reports nothing new.
- [x] 1.2 Add a regression test in `src/scantpaper/tests/test_simplelist.py`
  asserting that a constructed `SimpleList` reports
  `get_enable_search() is False` (the mechanism that makes the GTK critical
  unreachable), and the matching assertion for a constructed `BaseDocument`
  in `src/scantpaper/tests/test_basedocument.py` (inherited coverage).
  Verify: `pytest src/scantpaper/tests/test_simplelist.py
  src/scantpaper/tests/test_basedocument.py -q` passes and the new tests are
  collected.

## 2. Documentation

- [x] 2.1 Add a user-visible note to `README.md` recording that list widgets
  no longer open the (non-functional) typeahead search overlay and that the
  startup `gtk_css_node_insert_after` critical no longer appears. Verify:
  `pytest src/scantpaper/tests/test_markdown_line_length.py -q` passes and
  the added lines are wrapped at 80 characters.
- [x] 2.2 Record the upstream advisory - that this GTK bug should be reported
  upstream (GNOME GTK, deprecated GtkTreeView typeahead CSS-node assertion,
  still present in gtk-4-24) - in the code comment added in 1.1. Verify: the
  comment names the upstream bug and the workaround.

## 3. Integration Verification

- [x] 3.1 Run the full suite and qualify gates: `pytest` exits 0 with the
  configured coverage thresholds met and no new uncovered lines outside
  `TYPE_CHECKING` imports; `ruff check` and `ruff format --check` are clean.
- [x] 3.2 Run the manual end-to-end check used to diagnose the bug: launch
  the app under Xvfb with a copied `scantpaperrc` (auto-open-scan-dialog on),
  inject a printable key via the XTEST probe, and confirm no
  `css_node_insert_after` critical appears in stderr. Verify: the captured
  output contains no Gtk-CRITICAL for `css_node` while the list widget has
  focus.

## Workflow follow-up

- After the artifacts are reviewed and approved, start implementation with
  /opsx-apply.
- Archive the change once the project's review and release requirements are
  satisfied.
- Consider filing the upstream GTK issue (out of repo scope; tracked by 2.2).
