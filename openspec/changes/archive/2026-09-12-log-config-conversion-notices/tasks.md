## 1. Message routing in config.py

- [x] 1.1 `_normalise_types`: successful coercions log at INFO (English) and
      no longer append to `load_warnings`
- [x] 1.2 `_normalise_types`: failed coercions keep the translated
      `load_warnings` entry and additionally log it at WARNING
- [x] 1.3 `read_config` salvage branch: rescue notices additionally log at
      WARNING (both the rescued-settings and all-reset forms)

## 2. Tests

- [x] 2.1 `test_8_config.py`: success conversion asserted via `caplog` (INFO)
      and absent from `load_warnings`
- [x] 2.2 `test_8_config.py`: failed conversion still in `load_warnings` and
      also in the WARNING log
- [x] 2.3 `test_8_config.py`: rescue notice still in `load_warnings` and also
      in the WARNING log
- [x] 2.4 Run `pytest` and run the formatting/lint gates (ruff format, ruff
      check); coverage compares equal or better than before

## 3. Docs

- [x] 3.1 README.md "Configuration" section: conversions are logged, only
      actionable notices appear in the dialog
- [x] 3.2 changelog.md entry describing the change