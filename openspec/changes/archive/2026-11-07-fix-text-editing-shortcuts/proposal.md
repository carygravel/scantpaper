# Proposal

## Why

Standard text editing is unusable in the slice text control and other text
fields in the main window. GTK4 application accelerators intercept `+`, `-`,
`Ctrl+X`, `Ctrl+C`, `Ctrl+V`, `Ctrl+A`, `Ctrl+Z` and `Ctrl+Shift+Z` before the
focused text widget sees them. Typing a minus or plus sign therefore zooms the
image instead, and `Ctrl+X`/`Ctrl+V` operate on pages rather than text, so a
user trying to edit OCR output can restructure the document by accident.

This is a regression from the GTK3 to GTK4 accelerator migration and affects
layer editing in both tabbed and split views. The same text control exists in
both, so split view only makes the problem easier to notice.

## What Changes

- Text controls keep their standard editing keys: when the focused widget
  consumes a key, the corresponding window action does not run.
- `+` and `-` type normally in a text control. Outside a text control they
  continue to zoom in and out, as documented today; the mouse wheel continues
  to zoom everywhere.
- `Ctrl+X`, `Ctrl+C`, `Ctrl+V`, `Ctrl+A`, `Ctrl+Z` and `Ctrl+Shift+Z` perform
  text cut/copy/paste/select-all/undo/redo in a text control, and page
  cut/copy/paste/select-all/undo/redo everywhere else.
- The same page and view actions remain available from the menus and toolbars,
  so nothing becomes unreachable while a text control has focus.
- The plain `Delete` page shortcut continues to work outside text controls, and
  its handler ignores modified Delete presses so that text-editing variants are
  not mistaken for a page delete.
- The README's keyboard shortcut documentation states the context-sensitive
  behaviour.

No page selection, page clipboard, layer-editing, undo/redo, or zoom mechanics
change. All documented shortcuts remain available in their intended context, so
this is not a breaking change.

## Capabilities

### New Capabilities

- `keyboard-shortcut-scoping`: how application-level shortcuts defer to the
  focused text control, and how the same keys continue to drive page and view
  actions when focus is elsewhere.

### Modified Capabilities

<!-- None: the page and view action requirements are unchanged; only the
     precedence of the keyboard shortcut versus a focused text control is new. -->

## Impact

- `src/scantpaper/app.py`: remove the conflicting shortcuts from the
  application-level accelerator table.
- `src/scantpaper/app_window.py`: handle the affected keys in the existing
  bubble-phase window key controller, after the focused widget has had its
  chance.
- `src/scantpaper/tests/test_app.py` and
  `src/scantpaper/tests/test_app_window.py`: cover the accelerator table and
  the context-sensitive key handling.
- `README.md`: document that text controls keep standard editing shortcuts and
  that zoom keys act outside text controls.
- No new dependencies, database changes, or asynchronous workflow changes.
