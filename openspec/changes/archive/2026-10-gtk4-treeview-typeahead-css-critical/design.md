# Design

## Context

Every `GtkTreeView` scantpaper creates is a `SimpleList` (the document's
thumbnail list is a `BaseDocument`, which subclasses `SimpleList`; the
crashed-session picker constructs `SimpleList` directly). GTK 4.24's
deprecated treeview interactive (typeahead) search trips an upstream
`gtk_css_node_insert_after` assertion on the first printable keypress
(`gtk_tree_view_ensure_interactive_directory` inserts the search popover's
CSS node after the treeview `header` node, whose CSS parent does not match).
The bug is still present in the `gtk-4-24` branch (4.24.2). See
proposal.md - Why for the reproduction details.

Two gating facts, verified in source and by experiment:

- The popover is only created when `priv->enable_search` is true; the
  treeview's key-forward handler returns before calling
  `ensure_interactive_directory` otherwise.
- `SimpleList` never configures a search column (`search_column` stays -1),
  so typeahead currently shows nothing useful - it only emits the warning.

## Goals / Non-Goals

**Goals:**

- Eliminate the GTK critical from every list widget with one, minimal,
  maintainable change.
- Keep list behaviour (multiple selection, drag-and-drop, row editing)
  untouched.
- Add a deterministic regression test that guards the mechanism.

**Non-Goals:**

- Porting `SimpleList`/`BaseDocument` off deprecated `GtkTreeView` (a large,
  separate effort).
- Patching or suppressing GTK internals, or globally silencing GLib
  criticals.
- Fixing the upstream GTK bug itself (out of reach of this repo; see the
  advisory note instead).

## Decisions

**Decision 1: Disable typeahead search in `SimpleList.__init__`, not in
`BaseDocument`.**

`SimpleList` is the single choke point: the thumbnail list (via
`BaseDocument`) and the crashed-session picker (direct) both inherit the
change. Adding `self.set_enable_search(False)` right after
`super().__init__()` in `SimpleList` covers the whole application.

- Alternative (disable only in `BaseDocument`) rejected: the
  crashed-session picker `SimpleList` would stay affected.
- Alternative (intercept and cancel the search popover per keystroke)
  rejected: it fights GTK internals; `enable_search` is the supported,
  documented toggle and is the exact gate checked before popover creation.

**Decision 2: Use `set_enable_search(False)`; do not also set a search
column.**

`enable_search` is the predicate the key-forward handler evaluates before
creating the popover, so it is the precise lever. `set_search_column(-1)`
would not prevent popover creation and is therefore not needed.

**Decision 3: Regression test asserts the mechanism; end-to-end key injection
stays a manual/repro step.**

GTK 4 removed `gtk_test_widget_send_key`, so a unit test cannot inject a real
keystroke without OS-level input tooling. The deterministic, meaningful test
is that a constructed `SimpleList` and `BaseDocument` report
`get_enable_search() is False` - the gating condition that makes the critical
unreachable by construction. An optional end-to-end validation (Xvfb + XTEST
key injection, which was used to diagnose the bug) is documented as a
repro/steps task, not a CI test, so it does not introduce a new test-only
dependency or timing flakiness.

## Risks / Trade-offs

- [An upstream GTK release could fix the bug, after which the disabled
  search is a (harmless) leftover and a future author might genuinely want
  typeahead on a capa list] → The code comment cites the GTK bug and notes
  that re-enabling search requires the upstream fix; re-enabling stays a
  deliberate, documented act.
- [Silently losing typeahead on lists where someone later sets a search
  column] → `SimpleList` sets no search column today; any future
  implementation must consciously re-enable search, at which point the
  comment forces a re-check of the GTK bug.
- [Minimal behavioural loss if the search overlay was ever used] → The
  overlay currently shows nothing (no search column); verified the typeahead
  feature is dead weight in this application.
