# Design

## Context

See `proposal.md` — Why. The two padding layers and their code sites are
established there. Relevant current-state facts:

- Most dialogs subclass `Dialog` (`src/scantpaper/dialog/__init__.py`), which
  wraps `Gtk.Dialog`; `get_content_area()` returns the GtkBox that dialog
  builders append to. Five dialogs are built on a bare `Gtk.Dialog` instead
  (pick crashed session, pages to extract, and the three profile dialogs in
  `dialog/scan.py`), so they bypass the base.
- GTK4 CSS cannot set a `GtkBox`'s `spacing` (it is a widget property, not a
  CSS property). CSS could set a content `padding` but not inter-child
  spacing, so a CSS-only fix cannot satisfy the row-spacing requirement.
- Several tests build real `Dialog` instances (`test_05_dialog.py`) and others
  patch `Gtk.Box` / `Dialog` in the dialog modules.

## Goals / Non-Goals

**Goals:**

- One place that owns the dialog outer inset and the vertical spacing between
  content-area children.
- A single source of truth for the two values, shared by code and tests.
- No per-dialog opt-in: a dialog built on `Dialog` is padded automatically.

**Non-Goals:**

- Redesigning any dialog's structure, order, or labels.
- Restyling action buttons (that is `dialog-buttons`).
- Theming or matching a specific desktop theme's metric.
- Changing what size the scan dialog opens at.

## Decisions

**D1. Apply the outer inset and content-area spacing in the `Dialog` base,
not per dialog.** `Dialog.__init__` sets the content area's margins and
spacing once. Rationale: it is the actual regression site (the GTK3
theme-derived inset was replaced by a literal 0), it keeps every dialog
consistent, and it cannot drift across the nine Tools builders plus scan,
save, preferences, crop and unpaper. Alternative: patch only the Tools
builders — rejected as nine copies of the same two calls that will diverge.
The five dialogs that do not subclass `Dialog` route through the shared
`pad_content_area()` helper instead (see D6).

**D2. Express the values as shared constants in `const.py`.** Add
`DIALOG_CONTENT_MARGIN` and `DIALOG_ROW_SPACING`. Rationale: AGENTS.md
requires a constant used across modules (code and tests) to live in
`const.py`; both layers and their tests then read from one source.
Alternative: a CSS provider at APPLICATION priority — rejected because it
cannot set box spacing (see Context) and would split the mechanism across
Python and CSS.

**D3. Use `GtkBox` spacing rather than per-child margins.** The vertical
spacing lives on the content area, which separates the page-range frame from
the first row and each row from the next; the horizontal spacing lives on each
row box, separating a label from its control and unit. Rationale: `spacing` is
the idiomatic `GtkBox` mechanism and needs one call per box instead of one
margin call per child. Alternative: `set_margin_*` on every child — more
calls, and it duplicates the value at every site.

**D4. Set row spacing via the `Gtk.Box(spacing=...)` constructor at each row
site.** Sites are in `tools_menu_mixins.py`, `dialog/crop.py`, `unpaper.py`,
`postprocess_controls.py`, and — because Requirement 3 covers every dialog —
also `dialog/scan.py`, `dialog/save.py`, `dialog/preferences.py`,
`dialog/pagecontrols.py`, `dialog/sane.py`, `scan_menu_item_mixins.py`,
`pagerange.py`, `file_menu_mixins.py` and `edit_menu_mixins.py`.
Rationale: the smallest change, and the existing tests that patch
`scantpaper.tools_menu_mixins.Gtk.Box` keep working because the patched name
is still the one called. Alternative: a `helpers.dialog_row()` factory —
rejected because it would build a real `Gtk.Box` outside the patched module
and break those tests, and it hides the value behind an indirection for no
gain.

**D5. Keep `unpaper.py`'s margin-copy behaviour.** Its sub-boxes copy
`vbox.get_margin_top()` (`unpaper.py:260`, `:290`, `:441`, `:479`). With the
base now setting a non-zero content margin, those nested boxes inherit it as
their inset inside each frame, which is the intended result; no change is
needed there beyond the row boxes themselves.

**D6. Pad the five bare-`Gtk.Dialog` dialogs via a shared
`pad_content_area()` helper, not by subclassing `Dialog`.** The helper lives
in `dialog/__init__.py` and is called both from `Dialog.__init__` and from the
five ad-hoc builders (`session_mixins.py`, `file_menu_mixins.py`, and the
three in `dialog/scan.py`). Rationale: `Dialog.__init__` also installs
Escape/close-request handling, and those five dialogs are driven by
`helpers.run_dialog`, whose nested main loop quits only on a `response` — an
Escape that destroys the dialog without emitting a response would leave the
loop running. Sharing the padding function gives the same visible result
(inset + content spacing) with no change to their close semantics.
Alternative: convert each to the `Dialog` subclass — rejected for that reason,
and it would be a larger behavioural change than the bug fix requires.
Alternative: repeat the five margin calls at each site — rejected as the same
duplication D1 avoids.

## Risks / Trade-offs

- [The scan, save and preferences dialogs also gain the inset and spacing,
  shifting their layout] → Accepted: it is the same bug; run the full suite
  and the scan/save dialog tests. No requirement or persisted value changes.
- [A saved scan-dialog size now carries slightly more content, so a very small
  saved size looks tight] → Accepted: the user can resize; the persisted size
  is respected, not overwritten.
- [Base-class side effects touch mocked dialog instances in tests] → Mitigation:
  the added calls are plain `GtkBox` setters; `MagicMock`/`Mock` content areas
  absorb them, and `test_05_dialog.py` exercises the real widget.
- [The two values are aesthetic and may need tuning at review] → Mitigation: a
  single constant each; changing them touches no spec, approach or task.

## Migration Plan

Single coordinated change; no data or config migration. Rollback is reverting
the commit. Land with `pytest`, `ruff` and `ty` clean and the coverage
thresholds met.

## Open Questions

- The exact values (proposed `DIALOG_CONTENT_MARGIN = 12`,
  `DIALOG_ROW_SPACING = 6`) are aesthetic; confirm or adjust at review without
  changing the approach.
