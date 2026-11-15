# Design

## Context

- GTK 4.24 draws a `GtkButton.label` with an internal label whose
  `use-underline` is false by default (measured:
  `Gtk.Button().get_use_underline()` is `False`), so a marker is an
  accelerator only when that property is set.
- `app.ui` declares 33 translatable `label` properties on `GtkButton` and
  `GtkToggleButton` objects and sets `use-underline` nowhere.
- `helpers.labelled_icon_button()` builds a `GtkButton` around a box
  holding an icon and a plain `Gtk.Label`, and sets the accessible label
  explicitly from the same string.
- The catalogs were authored against GTK3 menus that did interpret the
  marker, which is why translations carry one for a string that now
  reaches a button.
- The template is assembled by extracting Python and GtkBuilder sources
  separately and merging the results with `msgcat --use-first`.

See `proposal.md` for why this matters; the requirements are in
`specs/mnemonic-rendering/spec.md` and `specs/translations/spec.md`.

## Goals / Non-Goals

**Goals:**

- A mnemonic marker is an accelerator wherever a translated label is
  displayed, whether the button comes from `app.ui` or is built in code.
- The invariant survives buttons added to `app.ui` later, without anyone
  remembering to set a property.
- The generated template names every source of a msgid.

**Non-Goals:**

- No catalog is edited and no msgid is added, removed or reworded.
- Not deciding where a translation should place its mnemonic; the
  existing decision that accelerator positions are not checked stands.
- Not introducing mnemonics for strings that have none.

## Decisions

**Enable mnemonics once, for every labelled button loaded by the
builder.** A module-level helper in `helpers.py` walks
`Gtk.Builder.get_objects()` after `add_from_file()` and sets
`use-underline` on each object that is a `Gtk.Button` with a non-empty
`get_label()`, and `ApplicationWindow` calls it.

- Why: one place instead of 33 property lines, and a button added to the
  `.ui` later inherits the behaviour. `get_objects()` returns the loaded
  objects in GTK4 (verified).
- Alternative rejected: 33 explicit `<property name="use-underline">`
  entries. Declarative and greppable, but a new button regresses the
  behaviour silently, and the XML diff is large for no gain.
- The test asserts the invariant over the loaded window, so it fails for
  a `.ui` label that is left out by either mechanism.

**`labelled_icon_button()` builds its label with
`Gtk.Label.new_with_mnemonic()`.** Equivalent to setting the property by
hand, but it states at the call site that the string may carry a marker.

**The accessible name is derived from the label with the marker
stripped.** The button sets its accessible label from the incoming
string, which GTK never normalises. (Measured: the label's own stored
text already drops the marker once `use-underline` is on, so `get_text()`
cannot recover it.) Stripping follows GTK's own rules: a single `_` is
consumed as the marker, `__` yields one literal underscore.

- Verified parsing: `_Löschen` yields key L, `Lö_schen` yields key s,
  `__Löschen` yields no key.
- Alternative rejected: drop the explicit accessible label and rely on
  GTK deriving one from the child label. The label is wrapped in a box
  rather than set as the button's `label`, and relying on the child walk
  would change what is announced if the layout changes.

**Merge the intermediate templates without `--use-first`.** Both inputs
are templates with empty `msgstr`, so there is no translation for the
flag to prefer; it only discards the second entry's references
(measured: with the flag, `Delete` lists only the Python sources; without
it, the `.ui` references are kept). The msgid set is unchanged either
way, so the existing extraction requirement still holds.

- Alternative rejected: stitching references with a post-processing
  pass or `msgmerge`. More code to reproduce what the default merge
  already does.

## Risks / Trade-offs

**A translated marker now creates a real accelerator, so two buttons in
one popover that choose the same letter make GTK ignore both** ->
accepted. No dialog action depends on these accelerators, and a literal
underscore in the label is worse.

**A translation that used `_` as literal text would lose it** ->
mitigation: no button-label msgid contains a non-mnemonic underscore
today, and `__` remains the documented escape, pinned by a scenario.

**The builder walk also reaches Button subclasses that happen to carry a
label** -> harmless: a marker only appears if a translator adds one.

**Stripping reimplements GTK's parsing rules, which could drift** ->
mitigation: unit tests pin the leading, mid-string and doubled cases, so
a GTK change shows up as a test failure rather than a wrong
announcement.

## Migration Plan

No data or configuration migration. After the change, catalogs that
already carry a marker start showing it as an accelerator, which is what
the translators intended. Reverting the commit restores the previous
rendering; no session state depends on it.
