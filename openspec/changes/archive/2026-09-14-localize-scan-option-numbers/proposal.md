## Why

A user in a decimal-comma locale (e.g. `de_DE.UTF-8`) who opens the scan
dialog sees numeric scan-option values rendered with a period — a resolution
list shows `215.9` and a free-text numeric option shows `115.2` — even though
the store and the driver use plain numbers. Typing a value with the locale's
decimal separator into a free-text numeric option (`115,2`) is passed
verbatim to the SANE backend; a FIXED option that the driver parses with
`float()` fails. The same string can also crash the pre-v3 profile import,
where `_coerce_option_value` calls `float()` directly on config text.

The paper-sizes editor already gained locale-aware parsing and display via
`helpers.decimal_separator()` (change `localize-decimal-separator`); numeric
scan-option values are the natural next candidates. This change reuses that
helper so the two surfaces behave identically.

## What Changes

- Scan-option **combobox/list items** with numeric values display using the
  locale decimal separator (`215,9` in a comma locale) instead of `str()`.
  String-valued items keep their existing translation (`d_sane`) rendering.
- Scan-option **free-text entry** widgets display numeric defaults with the
  locale separator, and typed text is parsed to the option's numeric type so
  `115,2` is sent to the backend as `115.2` for FIXED options (period input
  keeps working). Non-numeric (string) options are untouched.
- **Pre-v3 profile import** (`_coerce_option_value`) normalizes a decimal
  comma in string values before `float()`, instead of raising `ValueError`.
- No change to how values are stored (profiles keep canonical numbers), to
  unpaper's comma-joined config text, to subprocess file formats, or to the
  `%r` user-defined-tool substitution.
- The shared `format_number()` / `parse_number()` helpers become the single
  formatting/parsing path, also used by the paper-size editor renderer.

## Capabilities

### New Capabilities

- `scan-option-values`: numeric scan-option values are displayed and entered
  with the user's locale decimal separator, and the backend receives
  canonical numbers.

### Modified Capabilities

- `paper-size-editor`: reuses the shared formatter; behaviour unchanged.

## Impact

- `src/scantpaper/simplelist.py` — `float_g_cell_renderer` and
  `do_text_cell_edited` delegate to the shared helpers (behaviour identical).
- `src/scantpaper/helpers.py` — two small functions built on the existing
  `decimal_separator()`: `format_number(number)` and `parse_number(text,
  number_type=float)`.
- `src/scantpaper/dialog/sane.py` — `_create_widget_combobox` and
  `_create_widget_entry` use the locale-aware display/parse paths.
- `src/scantpaper/dialog/scan.py` — `_set_combobox_widget`, `_set_entry_widget`
  display localized numbers; `_coerce_option_value` parses robustly.
- Tests in `test_helpers.py`, `test_simplelist.py`, and the SANE dialog test
  files.
- No dependency or config-schema changes.