## Why

Users who destructively scan books (cutting off bindings, removing pages one
by one) always align the intact outer page edge to the scanner rim so that a
fixed scan area yields equal, repeatable pages. Scanning in landscape mode
keeps scan time short, but forces a rotation on every page: fronts need 270°
and the flipped backs need 90°. Because flatbed batch mode is single-sided
and always applies the "facing" rotation, there is no way to automate this
alternation today, so users must manually rotate every second page (or
re-OCR pages corrected later), which is slow and error-prone.

## What Changes

- Add an **alternating-rotation toggle** for flatbed batch scanning: a new
  checkbox in the Postprocessing tab of the scan dialog, visible only when
  the selected source is the flatbed, batch scanning is allowed
  (`allow-batch-flatbed`), and more than one page is configured.
- When enabled, the rotation applied to page *k* of a batch alternates by
  parity: odd pages use the configured rotation angle and even pages use
  that angle plus 180° (modulo 360°), which is exact for a flipped sheet
  aligned to the same straight edge.
- The alternation is scoped to single-sided flatbed batches. ADF and
  duplex scanning behaviour is unchanged: rotation there continues to be
  driven solely by the "side to scan" setting.
- Parity is relative to position within a scan batch (1, 2, 3, ...) and
  resets at the start of each batch, so scanning a second book later keeps
  fronts upright.
- Rotation still happens before OCR/unpaper in the import pipeline, so OCR'd
  pages and previews are automatically upright with no re-scan or re-OCR.

## Capabilities

### New Capabilities
- `flatbed-alternating-rotation`: Automatically alternate the per-page
  rotation by parity in single-sided flatbed batch scans, controllable via
  an explicit toggle.

### Modified Capabilities
- `page-numbering`: Scope the existing requirement that "page-number parity
  SHALL NOT influence rotation" so that it applies only to the standard
  duplex side-based path, and explicitly permits parity-based alternating
  rotation when the new flatbed toggle is enabled.

## Impact

- `src/scantpaper/dialog/scan.py` / `pagecontrols.py`: visibility gating of
  the new toggle (flatbed + `allow-batch-flatbed` + `num_pages > 1`).
- `src/scantpaper/dialog/sane.py`: per-page side/rotation determination in
  the flatbed batch loop (`_insert_target`/`new_page_callback` path).
- `src/scantpaper/scan_menu_item_mixins.py`: `_new_scan_callback` picks the
  rotation angle; must honour the alternation flag and per-page parity.
- `src/scantpaper/postprocess_controls.py`: new toggle widget; interaction
  with `can_duplex` visibility of the two angle selectors on flatbed-only
  devices.
- `src/scantpaper/config.py`: persisted setting for the toggle and angles.
- `openspec/specs/page-numbering/spec.md`: requirement scoping (delta spec).
- Tests in `src/scantpaper/tests/`: new unit tests for parity selection,
  gating, and spec-delta coverage; existing flatbed/duplex tests must remain
  green.
- No new third-party dependencies.