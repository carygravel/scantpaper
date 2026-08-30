## Context

See proposal.md — Why. Relevant code state:

- The padding behavior under test is PIL's truncation tolerance, switched on
  globally at `page.py:19` (`ImageFile.LOAD_TRUNCATED_IMAGES = True`). There is
  no custom padding routine to relocate.
- The legacy test fabricates a 70x46 PPM (from ImageMagick `rose:`) whose body
  is truncated to 1000 bytes, imports it, and asserts the page round-trips at
  full size (verified via `identify` output and equal PPM byte size).
- Production `import_files` loads raw files from disk through
  `Page(filename=...)` (`importthread.py:287-339`), so truncated files are still
  possible there (unlike scans, which build in-memory PIL images).
- `test_1631_import_images.py` is the existing home for PPM import coverage
  (`test_import_ppm`, `test_import_corrupt_png`) and already uses
  `import_files` + `get_page_sync` + the `temp_db`/`temp_ppm` fixtures.

## Goals / Non-Goals

**Goals:**

- Preserve regression coverage for `LOAD_TRUNCATED_IMAGES` on the path where
  truncated files can actually occur (`import_files`).
- Eliminate the unresolved FIXME (and its pylint W0511) from the scan test.
- Keep `import_scan`'s own test surface intact (it is covered by other tests).

**Non-Goals:**

- Changing runtime behavior, `page.py`, `importthread.py`, or any production
  code.
- Extending truncation handling (e.g. detecting/logging truncated imports).
- Removing `import_scan(filename=...)` support — it remains a public API
  exercised by `test_51_process_chain.py`.

## Decisions

**1. Relocate to `test_1631_import_images.py` via `import_files`.**
The truncated file starts life as a `.pnm`; `test_import_ppm` proves
`import_files` accepts PPM already, so the relocated test needs only the
truncation step added. Its assertions can be simpler than the legacy ones: the
legacy `identify`/byte-size round-trip only worked because PPM is uncompressed;
asserting `page.image_object.size == (70, 46)` (the original `rose:` size) and
mode `"RGB"` captures the padding behavior directly and more robustly.
*Alternative considered:* keeping the test where it is and rewriting the FIXME
as a plain comment. Rejected — it leaves the coverage parked on a path that can
no longer receive truncated files, which is exactly the confusion the FIXME
created.

**2. Move the whole test rather than its truncation half.**
The legacy `test_import_scan` asserts *only* truncation padding; the rest of
scan-import behavior is covered by `test_51_process_chain.py`,
`test_pagecontrols.py:102`, and `test_0601_dialog_scan.py`. Splitting it would
leave a near-duplicate test.

**3. Preserve the construction method.**
Reuse the legacy technique — pipe `rose:` through ImageMagick, truncate to
1000 bytes — rather than fabricating a PPM by hand. It keeps `rose:`'s known
dimensions/depth as the oracle and stays consistent with `test_import_ppm`.

## Risks / Trade-offs

- **Behavior drifts under PIL's truncation handling** (e.g. a PIL upgrade
  starts rejecting truncated files, making the test fail). → This is the point
  of the test: it is the regression guard. If it fails, the correct response is
  to decide how truncation should behave, not to delete the test.
- **Truncated-file import may raise rather than pad in the new location.**
  → The legacy test exercises the same PIL path (`Page(filename=...)`) and
  passes today; the relocated test asserts the same behavior through
  `import_files`. If a difference emerges, it is a genuine finding worth
  surfacing, not a test bug.
- **Unused fixture after removal.** → If `temp_pnm`/`temp_ppm` become unused in
  `test_101_document.py` after removing the test, drop those fixture usages so
  pylint stays clean (fixtures live in `conftest.py`; only usages are removed).

## Migration Plan

Revertible test-only change: revert removes the new test and restores the old
one. No data, schema, or user-visible impact.