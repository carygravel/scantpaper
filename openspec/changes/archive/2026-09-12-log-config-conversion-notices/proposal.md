## Why

After the `resilient-config-loading` change, a config file with multiple
wrongly typed values floods the startup message dialog with one "has been
converted" notice per setting (e.g. "The setting downsample dpi is 150.0 and
has been converted to 150."). These are benign, fully automatic type
normalisations that the user cannot act on, and none of them are written to the
log either. Users should only see messages they can actually act on; everything
else belongs in the log.

## What Changes

- Successful (lossless) type coercions in `_normalise_types` are no longer
  added to `load_warnings`, so they never appear in the startup message dialog.
  Instead each conversion is written to the log at info level.
- Coercions that fail (value kept raw because it cannot be used as the expected
  type) stay in `load_warnings` and therefore in the message dialog, and are
  additionally written to the log at warning level.
- The rescue notices emitted when the config file fails to parse stay in the
  message dialog and are additionally written to the log at warning level.
- A config that parses but only needs type normalisation therefore no longer
  shows a dialog or defers the quit-time write; only genuinely broken values
  and unreadable files still do.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `config-loading`: Which config-loading problems are surfaced to the user in
  the message dialog vs. only written to the log.

## Impact

- `src/scantpaper/config.py`: `_normalise_types` message routing and logging in
  the salvage branch.
- `src/scantpaper/tests/test_8_config.py`: assertions on `load_warnings` /
  `logs` for coercion and rescue messages.
- `README.md` "Configuration" section and `changelog.md`: reflect that value
  conversions are logged rather than shown to the user.
- i18n: the success-coercion string no longer needs translating; the `.pot`
  file is regenerated at the next release (po files are not hand-edited).