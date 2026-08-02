## 1. Canonical suggestion list

- [x] 1.1 Add `self._suggestions` list as the deduped source of truth in `EntryCompletion.__init__`
- [x] 1.2 Change `add_to_suggestions()` to update `self._suggestions` and re-render the model
- [x] 1.3 Change `set_suggestions()` to replace `self._suggestions` and re-render the model
- [x] 1.4 Change `get_suggestions()` to return `list(self._suggestions)` (insertion order)
- [x] 1.5 Update `test_09_entry_completion.py` so existing add/get/dedup assertions still pass against the canonical list

## 2. Substring matching

- [x] 2.1 Add a match func to `EntryCompletion` via `set_match_func()` that matches `key.casefold()` in the suggestion (case-insensitive substring)
- [x] 2.2 Add a test: text occurring in the middle of a suggestion matches (spec: "Text occurs in the middle of a suggestion")
- [x] 2.3 Add a test: matching is case-insensitive (spec: "Case-insensitive match")
- [x] 2.4 Add a test: no suggestion matches when the text appears nowhere (spec: "No match")

## 3. Prefix-first ranking

- [x] 3.1 On the entry's `changed` signal, re-render the model with matches bucketed: exact/prefix matches first, then substring-only matches, then the rest
- [x] 3.2 Add a test: prefix matches are ordered before substring-only matches (spec: "Prefix matches before substring matches")
- [x] 3.3 Add a test: exact match ranks first (spec: "Exact match ranks first")
- [x] 3.4 Add a test: with inline completion enabled, the first suggestion is a prefix match (spec: "Inline completion uses the top-ranked match")
- [x] 3.5 Verify empty entry text renders suggestions in insertion order (no crash, no reorder)

## 4. Dialog integration

- [x] 4.1 Add a test using the `Save` dialog metadata entries that author suggestions are ranked (spec: "Author suggestions ranked")
- [x] 4.2 Add a test that keyword suggestions are ranked (spec: "Keyword suggestions ranked")
- [x] 4.3 Verify `update_config_dict()` persists suggestions in insertion order despite ranking (test in `test_dialog_save.py`)

## 5. Verification & release

- [x] 5.1 Add a `changelog.md` entry under an appropriate version
- [x] 5.2 Run the full test suite: `pytest` (check coverage is not reduced)
- [x] 5.3 Run `black` formatting check on changed files
- [x] 5.4 Run `pylint` on `entry_completion.py` and the touched tests (score not reduced)
