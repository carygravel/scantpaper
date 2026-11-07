# Design

## Context

See `proposal.md` for motivation and
`specs/layer-editing/spec.md` for the behavior contract.

The layer editor's control bar is a `LayerControls` widget containing a real
`Gtk.TextView` (`src/scantpaper/layer.py`). `LayerEditor.edit()` already
populates that text view, shows the control bar, updates the page selection and
applies the focus zoom, but it never moves keyboard focus into the text view.
The canvas click path, the navigation controls, add, duplicate and accept all
funnel through `edit()`, so that one method is the common focus point.

The previous shortcut-scoping change made the window's Delete handler defer to a
focused text input. That is correct once the text view has focus; this change
makes the text view the focused editing context when a slice is focused.

## Goals / Non-Goals

**Goals:**

- Give the layer text control keyboard focus whenever a slice becomes focused.
- Select the slice text so Delete clears it and typing replaces it immediately.
- Keep the same behavior for text and annotation layers.
- Leave focus alone when no slice is focused.

**Non-Goals:**

- Changing the text commit path, undo/redo, or focus zoom.
- Changing page deletion when the page list has focus.
- Mapping the canvas click position to a character offset inside the text view.
- Selecting individual words or characters inside the text view.

## Decisions

### Focus and select in `LayerEditor.edit()`

After the control bar is shown and the slice text is in the buffer, call
`grab_focus()` on `self.controls.textview` and select the buffer's whole text
with `select_range(start, end)`. `Gtk.TextBuffer.set_text()` leaves the
insertion mark at the end of the text, so selection is what makes Delete and
typing act on the OCR text immediately.

Alternative considered: leave the caret at the end. This makes Backspace useful
but Delete does nothing until the user moves the caret, which does not match the
reported workflow.

Alternative considered: focus the text view from the canvas press handler.
That would miss navigation, add, duplicate and accept, which all call `edit()`
directly. Focusing in `edit()` covers every path in one place.

Alternative considered: map the canvas click position to a text offset. This
adds coordinate and font-metric work for little benefit; the user can click
inside the control to place the caret precisely.

### Do not focus when there is no slice

`edit(None)` and `clear()` continue to empty the control without requesting
focus. This avoids pulling focus away from the page list or another control
when a slice disappears, and it avoids focusing an empty editing control.

### Keep the existing shortcut scoping unchanged

No change is needed in `app_window.py`. Once the text view has focus, the
bubble-phase window controller already leaves Delete, Ctrl+X/C/V/A/Z and
`+`/`-` to the text control. Page deletion remains available whenever the page
list has focus.

### Test the focus request at the `edit()` boundary

The unit tests use a mocked `LayerControls`, so they can assert that `edit()`
calls `grab_focus()` and selects the whole buffer, and that `edit(None)` and
`clear()` do not. The navigation, add, duplicate and accept paths already call
`edit()`, so one focus test at that boundary covers all of them. A live XTEST
smoke test exercises the real keyboard routing in tabbed and split views.

## Risks / Trade-offs

- [Focus follows a slice click, which may surprise a user who only wanted to
  inspect the slice] -> The control bar is the editing context and clicking the
  page list returns focus there; the change makes the editing intent explicit.
- [Selecting all text makes Delete clear the whole slice] -> The text is only
  committed on accept, so Ctrl+Z can restore it before accepting; clicking
  inside the control places the caret for character-level corrections.
- [`grab_focus()` has no effect on an unmapped control] -> `edit()` is only
  reached while the layer canvas and its control bar are on screen, and the
  call is harmless when the widget is not mapped.
- [A user clicks a slice and then clicks canvas whitespace] -> Focus remains in
  the text control, so Delete still edits text; the page is not deleted.
- [The annotation layer uses the same editor code] -> Its text control gets the
  same focus and selection behavior, which is the intended consistency.

## Migration Plan

No data migration is required. Reverting the focus and selection calls in
`LayerEditor.edit()`, the tests, and the README restores the previous behavior.
