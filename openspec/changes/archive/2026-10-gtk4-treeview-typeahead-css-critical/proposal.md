# Proposal

## Why

Starting scantpaper prints a GTK critical on the first keystroke that lands in
any of its list widgets:

```
Gtk-CRITICAL **: gtk_css_node_insert_after:
assertion 'previous_sibling == NULL || previous_sibling->parent == parent' failed
```

The trigger is the deprecated GtkTreeView "typeahead" search feature, not the
background scan dialog: on a printable keypress GTK creates the interactive
search popover and inserts its CSS node using the treeview's `header` node as
the previous sibling, which trips the assertion. We reproduced it with a
standalone GTK 4.24 program and inside scantpaper itself (Xvfb + XTEST key
injection), and confirmed it is still present in the latest `gtk-4-24` branch
(4.24.2). Every treeview scantpaper builds (the thumbnail panel and the
"Pick crashed session to restore" picker, all `SimpleList`/`BaseDocument`
instances) is affected, and no search column is ever configured, so the
feature currently does nothing but emit the warning.

## What Changes

- Disable GtkTreeView interactive (typeahead) search on every `SimpleList`
  instance, which covers the thumbnail panel and all other list widgets
  (e.g. the crashed-session picker), so typing with a list focused no longer
  creates the search overlay and no longer emits the CSS-node critical.
- Add a regression test asserting the typeahead search is disabled on
  construction of `SimpleList` (and `BaseDocument`, which subclasses it).
- Document the change and note the upstream GTK bug so it can be reported
  (the fix does not depend on an upstream release).
- No user-facing value is lost: typing on a list shows no search results
  today, so the removed overlay is dead weight.

## Capabilities

### New Capabilities

- `list-typeahead`: Governs whether the application's list widgets engage
  GtkTreeView interactive (typeahead) search, and guarantees that typing in a
  list never triggers the upstream GTK CSS-node assertion.

### Modified Capabilities

None. `thumbnail-display` is about painting thumbnails at their generated
size and is not changing.

## Impact

- `src/scantpaper/simplelist.py`: add `set_enable_search(False)` in
  `SimpleList.__init__` with a comment referencing the upstream bug.
- `src/scantpaper/basedocument.py`: inherits the change through `SimpleList`;
  no direct edit expected.
- Tests: `src/scantpaper/tests/test_simplelist.py` (and a check in
  `test_basedocument.py` if cheap).
- `README.md`: user-visible change note (GTK critical gone; no search
  overlay on lists).
- No dependency, API, or data-model changes.
