## 1. Make selection transient in config

- [x] 1.1 In `src/scantpaper/config.py`, remove the selection deserialisation
      branch from `read_config` so a stored `selection` key is no longer turned
      back into a `Gdk.Rectangle` on startup.
- [x] 1.2 In `src/scantpaper/config.py`, remove the selection serialisation
      branch from `write_config` and drop `selection` from `output` so the raw
      `Gdk.Rectangle` is never handed to `json.dumps`.
- [x] 1.3 Keep `"selection": None` in `DEFAULTS` so downstream reads of
      `settings["selection"]` continue to work.

## 2. Update tests

- [x] 2.1 Update the selection round-trip assertions in
      `src/scantpaper/tests/test_8_config.py` so that after
      `read_config`/`write_config` the selection is absent or `None`, not a
      deserialised rectangle.
- [x] 2.2 Search for and update any other tests that assert the selection
      survives a config write/read round-trip.

## 3. Verify behaviour

- [x] 3.1 Confirm at startup `settings["selection"]` is `None`, so
      `session_mixins.py` page-load re-application and `app_window.py` tool
      change restore are inert without further code changes.
- [x] 3.2 Run the full test suite (`pytest`), format with `ruff`, and check
      `ty check .` stays clean.
