## Context

See proposal.md - Why. Dialog buttons are created through two seams:
`Dialog.add_actions()` (used by most dialogs, maps button positions to
`Gtk.ResponseType.OK` then `CANCEL`) and direct `Gtk.Dialog.add_button()` /
`add_buttons()` calls. `Gtk.Dialog.add_button()` sets `use_underline(True)`,
so a label with a leading underscore renders with a working mnemonic.

## Goals / Non-Goals

**Goals:**
- Every dialog button shows a localised label instead of a GTK stock ID.
- Button mnemonics are kept, as the stock buttons had them.
- Prevent stock IDs from reappearing.

**Non-Goals:**
- Changing button text style elsewhere (the earlier port sweep already
  replaced `Gtk.STOCK_*` in file choosers with plain `_("OK")` labels; those
  stay as they are).
- Adding icons to buttons.
- Changing which callbacks run for which response.

## Decisions

**D1. Replace the literals at the call sites, not with a compatibility map
in `add_actions()`.** A map would only cover `add_actions()` callers, would
keep a dead vocabulary in the code, and would hide the actual UI text from
the reader. Explicit `_()`-marked labels also make the strings translatable
(stock IDs never were). Alternative considered: translating the legacy names
centrally in `Dialog.add_actions()` — rejected for the reasons above.

**D2. Label and mnemonic mapping:**

| stock ID | label |
|---|---|
| `gtk-ok` | `_("_OK")` |
| `gtk-cancel` | `_("_Cancel")` |
| `gtk-close` | `_("_Close")` |
| `gtk-apply` | `_("_Apply")` |
| `gtk-save` | `_("_Save")` |

Mnemonics match the GTK3 stock labels (Alt+O, Alt+C, Alt+A, Alt+S) and the
project convention that a button mnemonic is written as `_OK` in the label.
`Gtk.Dialog.add_button` enables underline rendering, so no extra call is
needed.

**D3. Tests select callbacks by position, not by label.** The updated tests
currently find a callback by its stock-ID string; they now use the button's
position in the list (index 0 = confirm, 1 = cancel for `add_actions`), which
is stable across label changes and cannot key on a stock ID again.

**D4. Guard test against reintroduction.** A test scans production sources
for the substring `"gtk-` and fails if it finds it, so a stock ID copied from
old code is caught immediately.

**D5. One real-dialog test for the observable behaviour.** The scan dialog's
dismiss button is inspected through `Gtk.Dialog.get_widget_for_response()`
and asserted to carry the localised label (not a stock ID), covering the
capability end to end.

## Risks / Trade-offs

- [Underscore mnemonics could clash if a dialog shows two buttons with the
  same mnemonic] → Each dialog has at most one confirm and one cancel
  button with distinct letters (O/A/S vs C); no clashes arise.
- [New msgids (`_OK`, `_Cancel`, …) need translations] → They fall back to
  English until translated (per the translations capability), which is no
  worse than the stock IDs, which were never translated.
- [A guard test scanning source text could false-positive on a comment or a
  legitimate string such as a CSS class] → The scan looks only for the
  `"gtk-` literal in production `.py` files, which has no legitimate use now
  that stock IDs are gone; comments that mention stock IDs are written
  without the quote character.
