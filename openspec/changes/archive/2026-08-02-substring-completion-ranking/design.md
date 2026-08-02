## Context

`EntryCompletion` (scantpaper/entry_completion.py) is a 58-line `Gtk.Entry`
subclass used for the four metadata fields in the save dialog (title, author,
subject, keywords — scantpaper/dialog/save.py:536). It builds a
`Gtk.EntryCompletion` with `set_inline_completion(True)` and a
`Gtk.ListStore(str)` model. Matching is GTK's default case-insensitive
**prefix** matcher; the model order is insertion order and is also what
`get_suggestions()` reads back, so it doubles as the persisted config order.
The completion never sets a match func, so it never customizes matching or
ordering.

## Goals / Non-Goals

**Goals:**
- Match suggestions on any substring of the suggestion, case-insensitively.
- Rank matches so exact/prefix matches appear before substring-only matches,
  keeping the existing inline completion sensible.
- Keep config persistence (suggestions saved to `~/.config/scantpaperrc`)
  stable and in insertion order.

**Non-Goals:**
- No changes to `save.py`, the `meta_*` properties, or config storage.
- No fuzzy ranking (e.g. Levenshtein), no scoring beyond the
  exact/prefix/substring buckets.
- No change to which fields get completion — still exactly the four metadata
  entries.

## Decisions

### D1. Custom match func for substring matching

Set `completion.set_match_func()` with a case-insensitive substring test:

```python
def _match(completion, key, itr, data):
    return key.casefold() in data[itr].casefold()  # data = model
```

The default matcher only does prefixes; GTK offers no substring option, so a
custom func is the only way. `casefold()` preserves the current
case-insensitive behavior (strictly better than `lower()` for non-ASCII).

### D2. Rank by reordering the model on "changed"

On every `changed` signal, partition the canonical suggestion list into three
buckets and rebuild the `ListStore` rows in that order:

```
key = "br"
  bucket 0: exact then prefix matches   "Brian", "breeze"
  bucket 1: substring-only matches      "Sabrina"
  bucket 2: rest                        "Jeff"
```

GTK displays popup rows in model order and inline-completes to the **first**
matching row, so model order *is* both the dropdown order and the inline
completion choice. Rebuilding from a canonical list is idempotent and cheap
(suggestions number in the tens at most).

Alternatives considered:
- **`Gtk.TreeModelSort` wrapper**: the sort func can't see the typed key (it
  compares row values only), so it needs the key stashed on the instance and a
  forced re-sort on every keystroke. More moving parts, no user-visible gain.
- **Incremental `model.move()`**: harder to reason about than a clean
  partition + rebuild.

### D3. Keep a canonical insertion-ordered suggestion list

Maintain `self._suggestions` (deduped, insertion order) as the source of
truth. `add_to_suggestions()` / `set_suggestions()` update it, and
`get_suggestions()` returns `list(self._suggestions)` instead of reading the
model. The model is re-rendered from this list in ranked order on each
keystroke.

Rationale: `save.py`'s `update_config_dict()` persists whatever
`get_suggestions()` returns. If it read the reordered model, merely typing in
the field would shuffle the saved suggestion order. Keeping insertion order
for persistence decouples "what we remember" from "how we display."

### D4. Keep `set_inline_completion(True)`

Ranking makes inline completion safe: the first matching row is always an
exact/prefix match, so GTK completes to a suggestion that starts with the
typed text — the classic behavior users expect. Disabling inline completion
would be a larger UX change than this task needs.

## Risks / Trade-offs

- **[Rebuilding the model on `changed` could race GTK's popup/inline state]**
  → The `changed` signal fires before GTK recomputes completion rows, and the
  lists are small, so the rebuild is invisible. If popup glitches appear,
  fall back to D2's `TreeModelSort` alternative.
- **[`get_suggestions()` changes from model order to insertion order]**
  → This is the intended fix for stable persistence; tests in
  `test_09_entry_completion.py` and `test_dialog_save.py` are updated to match.
- **[Substring matching is noisier than prefix matching]**
  → Ranking mitigates it: prefix matches are always shown first, and the
  popup is filtered, so the list stays short.

## Migration Plan

None — no persisted schema or data changes. Suggestions on disk are
re-loaded as before and re-rendered in ranked order at runtime.

Rollback: revert the change; the previous commit restores prefix matching.
