## 1. Config migration

- [x] 1.1 Add a helper in `config.py`, e.g. `_normalise_scan_options(value)`, that
  brings one scan-options dict to the canonical shape: add `frontend: {}` /
  `backend: []` when missing, and hoist a spurious `backend` key out of an
  existing `frontend` (the serialised misparse) back to the top level.
- [x] 1.2 Reuse the helper from `_normalise_profiles` for every named profile
  (replacing the current inline `setdefault` calls).
- [x] 1.3 Apply the same helper to `config["default-scan-options"]` in
  `_deserialise_and_migrate`, guarding against non-dict / `None` values.

## 2. Tests

- [x] 2.1 Add `test_8_config.py` cases: a backend-only legacy
  `default-scan-options` is loaded with `frontend` defaulted to `{}` and
  `backend` preserved; the corrupted `{"frontend": {"backend": [...]},
  "backend": []}` shape is repaired; a well-formed value is untouched; named
  profiles still normalise as before.
- [x] 2.2 Add `test_03_scanner_profile.py` coverage that a normalised legacy
  `default-scan-options` value round-trips through `Profile.get()` with both
  frontend and backend keys and the backend option tuples preserved.

## 3. Verification

- [x] 3.1 Run the full suite (`pytest`) and confirm no coverage regression.
- [x] 3.2 Run `ruff format` and `ruff check` on the touched files.
- [x] 3.3 Document the user-visible change in `README.md`.
- [x] 3.4 Re-test the reported scenario end-to-end with a legacy rc file and a
  clean `--log` run to confirm the scan dialog shows the stored values on
  startup and the saved rc keeps both keys.