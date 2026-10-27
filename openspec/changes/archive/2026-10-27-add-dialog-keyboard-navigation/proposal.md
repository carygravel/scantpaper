# Proposal

## Why

A keyboard-only user cannot leave the OCR dialog's "Advanced Tesseract engine
parameters" field with the Tab key: `Gtk.TextView` defaults to
`accepts-tab = True`, so the field consumes Tab instead of moving focus, and
there is no way to reach OK without reaching for the mouse. The same trap
exists on the other text views used in dialogs and editing controls.

## What Changes

- The OCR "Advanced Tesseract engine parameters" text view releases the Tab
  key, so focus can move on to the next control and reach OK / Cancel.
- The text-layer editing text view releases the Tab key, so keyboard users are
  not trapped in it.
- Ctrl+Tab and Ctrl+Shift+Tab keep moving focus forward and backward in these
  fields (a GTK built-in), pinned by a spec scenario so it cannot regress.
- Regression tests assert that these editable text views do not accept Tab.

Trade-off: with Tab moving focus, a literal tab character can no longer be
typed into these fields. That is acceptable because the advanced field holds
`name=value` engine parameters, one per line, where a tab has no meaning.

The read-only message-dialog body is deliberately out of scope: GTK only
inserts a tab when a text view is both editable and accepting Tab, so a
non-editable view already moves focus on Tab.

## Capabilities

### New Capabilities

- `keyboard-focus-traversal`: a text view used in a dialog or an editing
  control SHALL let the Tab key move focus to the next widget instead of
  consuming it, so every dialog remains operable without a pointer.

### Modified Capabilities

- (none)

## Impact

- `src/scantpaper/postprocess_controls.py` (OCR advanced parameters field,
  shared by the Tools ▸ OCR dialog and the scan dialog's OCR options)
- `src/scantpaper/layer.py` (text-layer editing control)
- Tests in `src/scantpaper/tests/`
- No configuration, database, or dependency changes.
