## Why

When scantpaper 3.0.x inherits a pre-v3 gscan2pdf configuration file, profiles
written by gscan2pdf 2.x may be stored as `{"backend": [...]}` with no
`"frontend"` key. The application then crashes at startup in the scan dialog
(`dialog/scan.py:422` does `profiles[profile]["frontend"]` unconditionally),
so users upgrading from gscan2pdf 2.x can never start the application at all,
even though their scanner is detected fine. A related latent typo in the
`Profile` constructor (`scanner/profile.py:20`) duplicates a key check and
would introduce a crash for exactly these legacy profiles if "fixed" naively.

## What Changes

- Legacy pre-v3 scan profiles that lack a `frontend` key are normalised during
  config loading so every profile always has both `frontend` and `backend`
  keys, matching the structure that `Profile.get()` writes.
- The profile list construction in the scan dialog tolerates profiles missing
  either key, so a malformed or legacy profile can never crash the application
  at startup.
- The duplicated `"frontend" in frontend` check in the `Profile` constructor is
  corrected so the combined-dict path (used for `default-scan-options`) is
  self-consistent and never key-errors on a dict missing one of the two keys.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `config-loading`: add a requirement that legacy profiles missing the
  `frontend` key are normalised during config migration so the application
  starts with profiles in effect instead of crashing.

## Impact

- `src/scantpaper/config.py`: profile normalisation added to
  `_deserialise_and_migrate`, next to the existing "remove undefined profiles"
  logic.
- `src/scantpaper/dialog/scan.py`: profile-list loop uses safe key access.
- `src/scantpaper/scanner/profile.py`: constructor combined-dict branch fixed.
- `src/scantpaper/tests/config.py`, `.../test_dialog_scan.py`,
  `.../test_03_scanner_profile.py`: new/updated tests for legacy profile shapes.
- No new dependencies, no schema or data-model changes.