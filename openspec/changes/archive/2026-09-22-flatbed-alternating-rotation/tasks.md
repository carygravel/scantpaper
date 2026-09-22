## 1. Configuration

- [x] 1.1 Add `"alternate rotation": False` default to `config.py` next to
      `rotate facing`/`rotate reverse`.
- [x] 1.2 Add a test in `test_8_config.py` asserting the new default and that
      saving/reloading preserves it.

## 2. Postprocessing toggle widget

- [x] 2.1 In `add_postprocessing_options()` (`scan_menu_item_mixins.py`), add a
      `Gtk.CheckButton` "Alternate rotation every 2nd page" with a book-scanning
      tooltip explaining odd = configured angle, even = angle + 180°, bound to
      `settings["alternate rotation"]`.
- [x] 2.2 In `clicked_scan_button_cb`, write the toggle state back to
      `settings["alternate rotation"]` and reset the batch parity counter to 0,
      alongside the existing rotate-angle reads.
- [x] 2.3 Add a test constructing the scan dialog and asserting the toggle
      widget exists, reflects the setting, and that `clicked_scan_button_cb`
      persists it.

## 3. Visibility gating

- [x] 3.1 Extend `_update_postprocessing_options_callback` to set the toggle's
      visibility from `flatbed_selected()` AND `allow_batch_flatbed` AND
      `num_pages > 1`, in addition to the existing `can_duplex` update.
- [x] 3.2 Connect the toggle visibility refresh to both `changed-scan-option`
      and `changed-num-pages` signals.
- [x] 3.3 Add tests: toggle hidden for ADF, hidden for flatbed with
      `num_pages == 1`, hidden when `allow-batch-flatbed` is off, visible for a
      flatbed batch with `num_pages > 1`.

## 4. Alternation in `_new_scan_callback`

- [x] 4.1 In `_new_scan_callback`, compute the effective rotation angle using a
      batch parity counter; when the guard is active (toggle AND
      flatbed_selected AND allow_batch_flatbed AND num_pages > 1), even pages
      receive `(rotate_facing + 180) % 360` while odd pages keep `rotate_facing`.
- [x] 4.2 Leave the `side == "reverse"` duplex branch untouched so ADF/duplex
      rotation semantics are unchanged.
- [x] 4.3 Add tests in `test_scan_menu_item_mixins.py`: alternating batch emits
      facing-angle then angle+180 for consecutive new-scans; toggle off (or
      non-flatbed source) leaves every page at the facing angle; a fresh batch
      restarts at odd.

## 5. Docs & translations

- [x] 5.1 Document the new feature in `README.md` (feature bullet under the scan
      section and/or a flatbed-book-scan FAQ entry).
- [x] 5.2 Regenerate the translation template with
      `PYTHONPATH=src python3 dev/generate_pot.py`; do not edit `po/*.po`.

## 6. Quality gates

- [x] 6.1 Run `ruff format` and `ruff check` on changed files; fix any findings.
- [x] 6.2 Run `ty check .` (Zed's ty binary) and fix any diagnostics.
- [x] 6.3 Run the full `pytest` suite; confirm no regressions and that
      uncovered/partially-covered line counts are no worse than before.
- [x] 6.4 Sync delta specs to main specs (`openspec sync-specs`), keeping the
      `page-numbering` parity rule scoped as drafted.