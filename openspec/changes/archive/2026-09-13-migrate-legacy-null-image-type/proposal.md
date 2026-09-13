## Why

gscan2pdf 2.x configs store the document type as JSON `null` (`"image type": null`)
when it has never been set. When scantpaper reads such a legacy value (either the
migrated config or a `gscan2pdfrc` re-imported on a clean start), the type
normalisation step warns on every startup that this "cannot be used as str" and
leaves the value `None`, even though the application default `"pdf"` is the
obvious, safe fallback. The value is then written back as `null`, so the warning
never goes away.

## What Changes

- Migrate `"image type": null` to the application default `"pdf"` when loading
  the config, instead of warning and keeping `None`.
- Log the migration at INFO level (lossless conversion, no message dialog).
- Ensure the next config write stores `"pdf"` rather than re-emitting `null`.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `config-loading`: normalise a legacy `null` image type to the default instead
  of warning and leaving it raw when the value is unset.

## Impact

- `src/scantpaper/config.py`: `_deserialise_and_migrate` (new migration step).
- `src/scantpaper/app_window.py`: unchanged (re-import of `gscan2pdfrc` is the
  trigger, not the fault).
- Tests in `src/scantpaper/tests/test_8_config.py`.
- No API, dependency, or data-model changes.