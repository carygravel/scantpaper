## 1. Config: default value and one-time migration

- [x] 1.1 Change `DEFAULTS["threshold tool"]` from 80 to 20 in `config.py`
- [x] 1.2 Add a one-time migration in `config.read_config()` that maps a legacy saved `threshold tool` value `v` to `100 - v`, gated on the stored config `version` predating the change (absent `version` treated as legacy)
- [x] 1.3 Add tests in `test_8_config.py`: a legacy value is migrated (e.g. 80 -> 20), a current-version config is not migrated, an absent `version` is treated as legacy, and the default is 20
- [x] 1.4 Update any existing tests in `test_8_config.py` / `test_app_window.py` that assert the old default or migration behaviour

## 2. Core transform in the worker thread

- [x] 2.1 Rewrite `do_threshold()` in `docthread.py` to use the colour-distance transform: black iff `min(R,G,B) < round(255 * (100 - threshold) / 100)`, computed via `ImageChops.darker(ImageChops.darker(R, G), B)`, output converted to 1-bit; add the `ImageChops` import
- [x] 2.2 Add unit tests for the transform: saturated colours (red, yellow) and light colours (pink, light blue) on white render black at the default threshold, near-white pixels render white, and the output is 1-bit
- [x] 2.3 Add a percent-semantics test: thresholding a greyscale image at the migrated value keeps pixels darker than the intended percent cut-off and renders lighter pixels white
- [x] 2.4 Update `test_211_tools.py` `test_threshold` (and any other docthread/tool tests) to match the new transform and threshold semantics

## 3. UI: relabel the threshold controls

- [x] 3.1 Relabel the threshold dialog slider in `tools_menu_mixins.py` as an ink-strength cutoff (e.g. "Ink strength" with a tooltip explaining higher = only stronger marks kept)
- [x] 3.2 Update `postprocess_controls.py`: change the `_threshold_value` default to 20 and relabel its spinbutton to match
- [x] 3.3 Update the UI tests in `test_tool_menu_mixins.py` and `test_postprocess_controls.py` for the new default value and labels

## 4. Documentation and verification

- [x] 4.1 Document the user-visible change in `README.md` (colour-aware threshold; new default; saved-value migration)
- [x] 4.2 Run `black` and `pylint` on the changed files; run the full `pytest` suite and confirm coverage and pylint score are no worse than before
