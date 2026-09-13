## Why

Custom paper sizes defined with sub-millimetre precision (e.g. `RPB_quer`,
115.2 × 174 mm) silently lose their fractional part in the paper-sizes editor:
opening the dialog truncates `115.2` to `115` on load, and typing decimals is
rejected outright. At scan resolutions (1 mm ≈ 24 px at 600 dpi) this can
misrepresent the intended document size by many pixels.

## What Changes

- The Width/Height/Left/Top columns of the paper-sizes list store and round-trip
  decimal millimetre values instead of truncating them to integers.
- Users may type fractional values (e.g. `115.2`) when defining or editing a
  paper size.
- The truncated values already persisted in existing config files are not
  retroactively repaired (no way to recover the lost digits), but any
  sub-millimetre values still present are preserved from load through edit
  and save.

## Capabilities

### New Capabilities

- `paper-size-editor`: the paper-sizes definition list in the scan dialog —
  its dimension columns preserve decimal precision and accept fractional
  input.

### Modified Capabilities

<!-- None: no existing spec covers paper-size editing. -->

## Impact

- `src/scantpaper/dialog/paperlist.py`: dimension column types (`int` →
  `double`).
- `src/scantpaper/simplelist.py`: `double` column handling already exists;
  verify integral values display without ambiguous trailing digits.
- `src/scantpaper/config.py` defaults and any consumers of `Paper` sizes
  (`scanner/options.py` `supports_paper`, `page.py` resolution matching) —
  all already numeric and float-safe; no change expected.
- Tests for the paper-sizes list and config serialisation.