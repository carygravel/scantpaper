# Proposal

## Why

A German tester on a Tumbleweed snapshot sees the Delete button styled
`_Löschen`: the catalog supplies a keyboard mnemonic, but the widget that
draws it cannot honour one, so the marker renders as a literal
underscore. 47 shipped entries in 14 catalogs are affected across five
buttons, because every translated button label is now drawn by a widget
whose `use-underline` is false, while the strings carrying the marker
were authored for menus that interpreted it.

## What Changes

- Enable mnemonics on the 33 translated button labels in
  `src/scantpaper/app.ui`, so a `_` in a translation underlines the next
  character instead of appearing in the text.
- Build the label in `helpers.labelled_icon_button()` with mnemonics
  enabled, and derive its accessible name from the label with the marker
  removed, so assistive technology never announces an underscore.
- Preserve every source reference when the template generator merges the
  Python and GtkBuilder message sets, so a msgid used in both lists both.
  Today `msgcat --use-first` keeps only the first entry's references, so
  `Delete` appears to come from a single button in the scan dialog when
  it is really three widgets.
- Assert the rendered state in tests: that a translated label's mnemonic
  is honoured and that its accessible name carries no marker. Comparing
  a button's label against the translated msgid cannot detect this
  defect, because both sides carry the same marker.
- Leave every catalog untouched. The marker is correct in the source; it
  is the renderer that discards it.

## Capabilities

### New Capabilities

- `mnemonic-rendering`: how a keyboard mnemonic supplied by a
  translation reaches the screen — it underlines a character in every
  button label the application builds and never appears as text, and the
  accessible name derived from that label excludes it.

### Modified Capabilities

- `translations`: the template generator keeps the source references of
  a msgid that appears in more than one input, so the generated catalog
  shows every place a string is used.

## Impact

- `src/scantpaper/app.ui`: `use-underline` on the 30 `GtkButton` and 3
  `GtkToggleButton` labels; the widget classes and layout are unchanged.
- `src/scantpaper/helpers.py`: `labelled_icon_button()`.
- `dev/generate_pot.py`: the `msgcat` merge of the two intermediate
  templates.
- `src/scantpaper/tests/test_icon_buttons.py` and new rendering tests.
- `po/scantpaper/scantpaper.pot` regenerated: references change, the
  msgid set does not.
- `README.md`: a translator-facing note in the Translations section that
  `_` marks a mnemonic and `__` is a literal underscore.
- `changelog.md`: an entry under 4.0.5.
- Every existing translation that carries a mnemonic starts showing it as
  an accelerator, which is what the translator intended. Two buttons in
  one popover that choose the same letter leave that accelerator
  inactive; no button loses its label, and no dependency changes.
