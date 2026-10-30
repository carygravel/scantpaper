# Proposal

## Why

In a resizable dialog, any row that requests vertical expansion absorbs the
surplus height the window has, so rows that should hug their content stretch
instead. In the scan dialog at 450x1000 the `# Pages` frame grows from its
natural 96 px to 728 px and its radio buttons spread apart; on the
Postprocessing page the `Rotate` row becomes 813 px tall; in the Clean up and
Preferences dialogs the rows spread away from each other.

The GTK3->4 migration rewrote `pack_start(..., expand=True)` as
`set_vexpand(True)`. GTK4 propagates an expand request up through containers,
so a flag that was invisible inside a frame in GTK3 now makes the frame itself
expand. `bb95c6be` fixed one instance, the page-range selector, and documented
the mechanism; the remaining instances were left in place, and the same
symptom keeps reappearing in a new dialog.

## What Changes

- A dialog row keeps its natural height when its dialog has surplus height.
  The surplus stays as blank space below the last row instead of being
  distributed to a frame, checkbox, or label/control row.
- Remove the stale vertical expand requests from:
  - the scan dialog's `Page Options` page (`# Pages` and `Source document`);
  - the scan dialog's `Postprocessing` page (`RotateControls`);
  - the Clean up (unpaper) dialog's option rows;
  - the Preferences dialog's `General options` page.
- Top-align the content of the scan dialog's notebook pages, so a page whose
  content is shorter than the window cannot hand surplus height to its rows.
- No change to widget order, labels, spacing, or any setting.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `dialog-layout`: adds a general requirement that dialog rows keep their
  natural height and that surplus height is not distributed to rows. The
  existing "page-range frame keeps its natural height" requirement becomes one
  instance of the general rule rather than a special case.

## Impact

- Code: `src/scantpaper/dialog/pagecontrols.py`,
  `src/scantpaper/postprocess_controls.py`, `src/scantpaper/unpaper.py`,
  `src/scantpaper/dialog/preferences.py`.
- Tests: `test_pagecontrols.py`, `test_postprocess_controls.py`,
  `test_34_unpaper.py`, `test_preferences_dialog.py`, plus a real-layout
  regression test that presents a tall scan dialog and checks row heights.
- Docs: `README.md` and `changelog.md`, because the layout change is
  user-visible.
- No API, dependency, settings, or data changes.
