## Why

Metadata suggestions in the save dialog (title, author, subject, keywords) only
match against the *start* of the current text. Typing "vox" never surfaces
"La Voz de Galicia", forcing users to retype the whole string even though a
suggestion already exists. `Gtk.EntryCompletion`'s default matcher is a
case-insensitive prefix match, so the limitation is inherited, not chosen.

## What Changes

- **Substring matching** in `EntryCompletion`: a suggestion matches if the
  typed text occurs anywhere in it, not just at the start.
- **Prefix-first ranking**: when the completion popup shows, exact/prefix
  matches are ordered above substring-only matches, which keeps inline
  completion sensible — the first suggestion inserted inline is always a
  prefix (or exact) match of what was typed.
- **Case-insensitive** matching, matching current behavior.
- Applies to all four metadata fields via the shared `EntryCompletion` widget;
  no per-field logic.

## Capabilities

### New Capabilities
- `entry-completion`: The metadata suggestion completion widget's matching and
  ranking behavior (substring matching, prefix-first ordering,
  case-insensitivity).

### Modified Capabilities
<!-- None — no existing spec covers entry completion. -->

## Impact

- **`scantpaper/entry_completion.py`**: Add a custom `Gtk.EntryCompletion`
  match func (substring) and reorder the suggestion model so prefix matches
  rank above substring matches on each keystroke.
- **`scantpaper/tests/test_09_entry_completion.py`**: Add tests for matching,
  ranking, and case-insensitivity.
- **`changelog.md`**: New entry.
- No changes to `save.py`, the `meta_*` properties, config persistence, or the
  dependency list.
