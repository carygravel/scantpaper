# Design

## Context

See `proposal.md` - Why, and `specs/dialog-layout/spec.md` for the required
behaviour.

Every row that absorbs surplus height does so because of a `vexpand` request
carried over from GTK3's `pack_start(..., expand=True, ...)`. GTK4 keeps no
per-child packing record, so `GtkBox` asks `gtk_widget_compute_expand()`, which
walks into containers: a frame holding an expanding checkbox reports itself as
expanding. The surplus then reaches the row because a GTK4
`Gtk.ScrolledWindow` allocates its child at the viewport size when the content
is shorter, and a `Gtk.Notebook` gives the current page the full content
height.

Verified by presenting each dialog at 450x1000 under Xvfb:

| Site | Natural | Allocated |
|------|---------|-----------|
| Scan `# Pages` frame | 96 px | 728 px |
| Scan `# Pages` "All" button | 19 px | 336 px |
| Scan `RotateControls` | 74 px | 861 px |
| Clean up "Deskew" checkbox | 27 px | 154 px |
| Clean up "Deskew" frame | 179 px | 311 px |
| Preferences General row | 34 px | 56 px |

The page-range selector already follows this rule after `bb95c6be`; its
requirement stays in the spec unchanged and is now one instance of the general
rule.

## Goals / Non-Goals

**Goals:**

- Rows keep their natural height in the scan, Clean up and Preferences
  dialogs.
- A notebook page that receives surplus height cannot hand it to its rows.
- Regression tests cover both the expand flags and the real allocated
  heights.
- Keep the existing scrolling behaviour for pages taller than the window.

**Non-Goals:**

- Redesigning the scan dialog, its pages, or their order.
- Changing dialog default or persisted sizes.
- Rewriting the page-range requirement or its implementation.
- Introducing a generic row widget or a new layout helper.
- Auditing dialogs outside the three named in the proposal.

## Decisions

### Remove the vertical expand requests

Remove `set_vexpand(True)` / `pack_box(..., expand=True)` where the parent is a
vertical box and the row is not meant to fill:

- `dialog/pagecontrols.py`: the "All" check button and the `#:` row in the
  `# Pages` frame, and the "Single sided" button and the "Side to scan" row in
  the `Source document` frame.
- `postprocess_controls.py`: `RotateControls._side1`. Its `_side2` sibling
  never had the flag, which shows the GTK3 asymmetry.
- `unpaper.py`: the row helpers `_add_combobox`, `_add_checkbutton`,
  `_add_checkbuttongroup`, `_add_spinbutton` and `_add_spinbuttongroup`.
- `dialog/preferences.py`: every `set_vexpand(True)` on a row appended to a
  vertical box in the General options page.

Only vertical requests are removed. `pack_box(..., expand=True)` on a
horizontal box still sets `hexpand` and is left alone.

Alternatives considered:

- **Leave the flags and rely on the page-level guard only**: fixes today's
  dialogs, but a page shown outside a scrolled window (or a future row added
  to a frame) would stretch again. The flags are the cause; the page-range
  change already established this reasoning.
- **Add `valign=START` to each frame**: rejected for the same reason as in
  `bb95c6be`; the frame would still claim the surplus in its parent box and
  leave a gap between itself and the next row.

### Top-align notebook page content

Set `valign=Gtk.Align.START` on the content box of each scan-dialog notebook
page: `PageControls._notebook_pages[0]`, the sane `_new_group_page` box, and
the Postprocessing `vboxp`. This matches the idiom already used by the
Preferences "Scan options" page.

With the flag removal alone the page box still fills the viewport and the
surplus is simply unallocated; the guard makes the intent explicit and keeps a
future stray `vexpand` from reaching a row. Width still fills, because
`halign` stays `FILL`.

Alternative considered: **drop the `Gtk.ScrolledWindow` and let the notebook
page fill directly** - removes the surplus entirely, but the dialog would no
longer scroll on a short screen, which the spec forbids.

### Give the Preferences General options page the same guard

`PreferencesDialog` already top-aligns its "Scan options" page but not its
"General options" page, which is why only the latter spreads. Add the same
`valign=Gtk.Align.START` and remove its row flags. This is a one-line guard
plus the flag removal, and it makes the two pages consistent.

### Test both the flags and the allocation

- Unit assertions that the affected rows do not request vertical expansion and
  that their containers do not compute as expanding, following
  `test_page_range_does_not_expand_vertically`.
- One real-layout test that presents a tall `Scan` dialog, pumps the main
  loop, and asserts the `# Pages` frame and the `All` button are at their
  natural heights. The suite already runs under Xvfb and
  `test_tool_menu_mixins.py` uses the same pattern.
- One layout test for a short window asserting the page still scrolls, so the
  top-align guard cannot silently break scrolling.

Allocation tests use a tolerance of a few pixels, because frame borders and
label allocation vary slightly between themes.

## Risks / Trade-offs

- **Xvfb allocation differs from a real window manager** -> assert
  `compute_expand` as the primary invariant and keep the allocation test's
  tolerance loose.
- **A future page legitimately needs to fill** (for example a text view) ->
  the page constructor must opt out of `valign=START`; document this next to
  the page helper.
- **Removing a flag that was load-bearing** -> the only vertical boxes
  involved are row stacks; the notebook and the dialogs' own content areas keep
  their `vexpand`, so the dialog still fills.
- **The Preferences dialog has two pages with different treatment** -> both
  end up top-aligned, so the inconsistency disappears rather than moving.
- **Scrolling regressions** -> covered by the short-window layout test.

## Migration Plan

None. There is no settings, data or file-format change; the change is confined
to widget layout and tests. Rolling back means reverting the code and tests.
