## 1. Tests for legacy profile handling

- [x] 1.1 Add a config migration test in tests/test_8_config.py: a config with
      `{"profile": {"p": {"backend": [...]}}}` (no `frontend` key) is
      normalised by `read_config` so the profile has both `frontend` and
      `backend` keys, with backend options unchanged
- [x] 1.2 Add a config test asserting a fully well-formed profile is left
      unchanged by the migration
- [x] 1.3 Add a dialog test in tests/test_dialog_scan.py: constructing
      `SaneScanDialog` with `profiles={"p": {"backend": [...]}}` does not
      raise and the profile is added with backend options intact
- [x] 1.4 Add a `Profile` constructor test in tests/test_03_scanner_profile.py:
      `Profile({"frontend": {...}})` with no `backend` key yields a proper
      combined profile instead of key-erroring, and
      `Profile({"some": "other"})` still stays a pure frontend dict

## 2. Core implementation

- [x] 2.1 Normalise legacy profiles in `config.py` `_deserialise_and_migrate`:
      default missing `frontend`/`backend` keys to `{}`/`[]` for every value
      in `config["profile"]` (design D1)
- [x] 2.2 Harden the profile loop in `dialog/scan.py` to use `.get()` with
      `{}`/`[]` defaults instead of unconditional key lookup (design D2)
- [x] 2.3 Collapse the duplicated key check in the `Profile` constructor
      (`scanner/profile.py`) into a single `"frontend" in frontend` guard
      with a `.get("backend", [])` (design D3)

## 3. Verification

- [x] 3.1 Run `ruff format` and `ruff check` on the changed files
- [x] 3.2 Run `pytest` and confirm the full suite passes with coverage
      thresholds met
- [x] 3.3 Update README.md changelog/notes with the user-visible fix