## 1. Tolerant load in config.py

- [x] 1.1 Add a `ConfigDict(dict)` subclass carrying a `load_warnings: list[str]`
      attribute, in `src/scantpaper/config.py`
- [x] 1.2 Split `read_config` into a pure JSON parse attempt plus a salvage pass:
      on `json.decoder.JSONDecodeError`, rename the file to `scantpaperrc.old`
      (as today), then regex-scan the file for `"key": <value>` fragments,
      keep fragments whose key is in `DEFAULTS` and whose value re-parses with
      `json.loads`, and return a `ConfigDict` with a warning describing the
      rescue
- [x] 1.3 Make `read_config` return a `ConfigDict` (empty `load_warnings` on a
      clean parse) so callers can detect a rescued/defaulted load
- [x] 1.4 Add conservative type normalisation in the load path: for each key in
      `DEFAULTS`, if the stored value's type differs from the default's type,
      attempt a lossless coercion (int/float/str/bool); on success record a
      warning, on failure keep the raw value and warn. Skip keys whose default
      is `None`
- [x] 1.5 Run `pytest` and `ruff` on `config.py` after the refactor

## 2. Protect the write path

- [x] 2.1 In `write_config`, stop mutating the caller's `settings` dict in place;
      serialise `device list` / `datetime offset` / `selection` on a copy so a
      later failure cannot leave the live settings half-serialised
- [x] 2.2 In `file_menu_mixins._can_quit`, skip `config.write_config` when the
      active settings carry load warnings and the user has not been informed
      yet, so a defaulted/rescued config is not silently written over the
      original rc file
- [x] 2.3 Ensure `write_config` never touches `scantpaperrc.old`

## 3. User notification

- [x] 3.1 In `app_window._read_config`, stash the load state
      (`self.settings.load_warnings`) on the window (e.g. a
      `_config_load_warnings` attribute) so it survives until the UI is ready
- [x] 3.2 After `show_all()` in `_populate_main_window`, if load warnings exist,
      raise a non-blocking `Gtk.MessageDialog` (INFO) listing which settings
      were rescued/defaulted and the backup path, and mark the user as informed
      (which unblocks the write path in 2.2)
- [x] 3.3 Add i18n markers (`_()`) for all new user-facing strings and note that
      `po/*.po` must not be edited manually (template via
      `dev/generate_pot.py`)

## 4. Tests

- [x] 4.1 Update `tests/test_8_config.py` for the return type and rescue
      behaviour: valid-file and round-trip assertions must still pass
- [x] 4.2 Add tests: unparseable file with intact `"rotate facing": 90` /
      `"rotate reverse": 270` rescues those keys, creates `scantpaperrc.old`,
      and reports a warning
- [x] 4.3 Add tests: string value `"rotate facing": "270"` is coerced to 270 and
      warning recorded; unrescuable wrong types keep raw value + warning
- [x] 4.4 Add tests: `write_config` does not mutate the caller's dict and does
      not write to `*.old`; `_can_quit` skips writing on uninformed rescued
      load and resumes writing once acknowledged
- [x] 4.5 Add a test for the notification wiring in `app_window` (warnings shown,
      user marked informed)

## 5. Docs & release pass

- [x] 5.1 Document the new behaviour in `README.md`: settings file failures are
      rescued, never silently reset, with a backup kept at
      `~/.config/scantpaperrc.old`
- [x] 5.2 Update `changelog.md` with the fix
- [x] 5.3 Final pass: full `pytest`, `ruff format`, `ruff check`, and confirm
      uncovered/partially-covered line counts are no worse than before