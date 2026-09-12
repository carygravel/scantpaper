## Why

A user migrating from gscan2pdf 2.x has a `default-scan-options` in the old
backend-only dict format (`{"backend": [{"mode": "Binary"}, ...]}` without a
`frontend` key). scantpaper 3.0.18's gscan2pdf-profile fix
(`2026-09-11-fix-legacy-profile-load`) normalises *named* profiles but assumes
`default-scan-options` is always well-formed, so a legacy-shaped
`default-scan-options` is silently ignored on startup — the scan dialog shows
device defaults, "as if the rc file were not loaded" — and the value is then
rewritten to the rc file in a corrupted shape on quit, making the failure
permanent.

## What Changes

- `default-scan-options` is normalised during config migration just like named
  profiles: a backend-only legacy value gains an empty `frontend` key.
- Legacy single-key-dict backend entries in `default-scan-options` are
  coerced to `(name, value)` pairs so they are applied on startup and survive
  the session, instead of being dropped and rewritten in a broken shape.
- Well-formed `default-scan-options` (the output of `Profile.get()`) is
  untouched.
- No change to how newly created scan options are stored.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `config-loading`: extend the existing legacy-profile normalisation
  requirement so that `default-scan-options` is covered in addition to named
  `profile` entries.

## Impact

- `src/scantpaper/config.py` — extend `_normalise_profiles` (or the migration
  step next to it) to also normalise `default-scan-options`.
- `src/scantpaper/scanner/profile.py` — already converts single-key-dict
  backend entries once the backend is reachable; no change expected, but the
  combined-dict branch may need to tolerate the legacy shape defensively.
- `src/scantpaper/scan_menu_item_mixins.py` — consumer unchanged; benefits
  from the normalised config.
- `src/scantpaper/tests/test_8_config.py`,
  `src/scantpaper/tests/test_03_scanner_profile.py` — new tests for the
  legacy `default-scan-options` load/round-trip.
- No new dependencies. No breaking changes.