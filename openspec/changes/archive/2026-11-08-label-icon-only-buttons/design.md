# Design

## Context

The Scan profiles frame, the paper-size editor, the profile editor and the
Preferences tool list build buttons as `Gtk.Button` plus
`Gtk.Image.new_from_icon_name(...)`. `layer.py` already has
`_make_icon_button`, which also sets a tooltip; the dialogs in scope do not use
it. The application registers its bundled icons from `src/scantpaper/icons` at
startup and otherwise uses the desktop icon theme. `document-edit` is not part
of the freedesktop icon set and resolves to `image-missing` in the `mate`
theme used here. See `proposal.md` for the user-visible problem.

## Goals / Non-Goals

**Goals:**

- Every audited icon-only button is identifiable by sight, keyboard and
  assistive technology, and shows a real icon.
- One reusable way to build such a button, so new ones do not repeat the gap.

**Non-Goals:**

- Redesigning the scan or preferences dialogs, or rearranging their layout.
- Changing action-button labels already covered by `dialog-buttons`.
- Adding keyboard mnemonics to content buttons; they are not action-area
  buttons.

## Decisions

**Visible labels where the row has room, tooltips elsewhere.** The profile
frame's Save/Edit/Delete buttons get visible text, because the row is not
dense and those words are already translated. Dense or repeated rows (paper
add/remove, per-row profile delete, Preferences add) stay icon-only and gain a
tooltip. Alternatives: tooltips only everywhere, which still requires hovering
to discover a feature; or labels everywhere, which crowds repeated rows.

**Set an accessible name in one helper.** Add a small helper that sets the
icon, tooltip and `Gtk.AccessibleProperty.LABEL` together, and use it for the
icon-only buttons. In GTK4 a tooltip becomes an accessible description, not a
name, so assistive technology would still announce an unnamed button.
Alternative: rely on the visible label for the profile frame and name only the
dense rows, at the cost of two conventions.

**Use symbolic icon names.** Replace `document-edit` with
`document-properties-symbolic`, and use the symbolic form of every audited
icon. Adwaita, the GTK default theme, ships only symbolic names: under it all
of the non-symbolic names resolve to `image-missing`, while mate provides
both. The symbolic names resolve in both themes tested. If a target theme
later lacks one, bundle it under
`src/scantpaper/icons/hicolor/scalable/actions/`. The Save dialog's
calendar-edit button shares the name and changes with it. Alternative: bundle
each icon immediately, which adds assets whose licence and packaging must be
tracked.

**Test what a user can observe.** Walk each audited dialog and assert that
every icon-only button has a tooltip or a visible label, a non-empty accessible
name, and that every icon name used resolves with `Gtk.IconTheme.has_icon`.
Alternative: a source-level grep test, which would not prove the icon actually
resolves in a theme.

## Risks / Trade-offs

- Symbolic names may be absent from an unusual theme. → Adwaita and mate both
  provide the audited names; the bundled-icons path is the fallback if a target
  theme lacks one.
- New tooltip strings add translation work. → Reuse the existing Save/Edit/
  Delete msgids for visible labels, and keep tooltips short and specific.
- Visible labels widen the profile frame. → The frame already spans the dialog
  width, and the three words fit in the space the Save button currently
  stretches over.

## Migration Plan

None. The change is limited to how the dialogs build their buttons; no stored
state changes.
