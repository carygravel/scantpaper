# Tasks

## 1. Shared icon-button helper

- [x] 1.1 Add a helper that builds an icon button with a tooltip and an
      accessible name (`Gtk.AccessibleProperty.LABEL`), and verify with a unit
      test that constructing it applies both.
- [x] 1.2 Replace the hand-built icon buttons in the audited dialogs with the
      helper where they stay icon-only, and verify each dialog still builds
      and its existing tests pass.

## 2. Visible labels and tooltips

- [x] 2.1 Give the Scan profiles Save/Edit/Delete buttons visible labels using
      the existing "Save", "Edit" and "Delete" msgids, and verify a test finds
      each button by its label.
- [x] 2.2 Add tooltips to the add/remove buttons in Edit paper size, the
      per-row delete buttons in Edit profile, and the add button for
      user-defined tools in Preferences; verify each button exposes a
      non-empty tooltip and accessible name in a test.
- [x] 2.3 Keep the Save dialog's calendar-edit tooltip and verify it still has
      one after the icon change.

## 3. Icon names

- [x] 3.1 Replace `document-edit` with `document-properties` in
      `dialog/scan.py` and `dialog/save.py`, and verify a test asserts
      `Gtk.IconTheme.has_icon("document-properties")` in the test theme.
- [x] 3.2 Add a guard test that fails when an audited button references an
      icon name the test theme does not provide.

## 4. Translations, documentation and quality gates

- [x] 4.1 Run `PYTHONPATH=src python3 dev/generate_pot.py` and
      `PYTHONPATH=src python3 dev/check_po.py`; verify the catalogs pass, and
      add any new tooltip msgids to the catalogs as `#, fuzzy` entries only if
      translating them now.
- [x] 4.2 Document the profile controls in `README.md` and add a
      `changelog.md` entry under 4.0.4 describing the more identifiable
      buttons; verify the README table-of-contents link resolves.
- [x] 4.3 Run `ruff format`, `ruff check`, `ty check .`, `pytest` and
      `python3 dev/check_test_coverage.py`; verify all pass and coverage stays
      at or above the gate.

## Workflow follow-up

- Archive the change after the project's review requirements are satisfied.
