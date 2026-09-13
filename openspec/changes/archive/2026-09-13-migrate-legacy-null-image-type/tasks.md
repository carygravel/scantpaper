## 1. Config migration

- [x] 1.1 In `src/scantpaper/config.py`, add a migration step to
  `_deserialise_and_migrate`: when `config.get("image type") is None`, set it to
  `DEFAULTS["image type"]` ("pdf") and log the migration at INFO level.
- [x] 1.2 Verify the migration runs before `_normalise_types` so no `image type
  is None` WARNING is emitted for the migrated value.

## 2. Tests

- [x] 2.1 Add a `test_8_config.py` migration test: a config containing
  `{"image type": null}` loads with `image type == "pdf"` and
  `config.load_warnings` is empty.
- [x] 2.2 Add a round-trip test proving the migrated value is written back as
  `"pdf"` rather than `null` on the next config write.
- [x] 2.3 Assert the E2E scenario in the reporter's log: starting the real
  application (via `read_config` on a migrated `scantpaperrc`) produces the
  INFO migration line and no `image type is None` warning.

## 3. Verification

- [x] 3.1 Run the full pytest suite and confirm coverage (>= 99) and no
  regressions.
- [x] 3.2 Run `ruff format` and `ruff check` on the touched files.
- [x] 3.3 Optionally update `changelog.md`/`README.md` if a startup-warning
  change is user-visible.
