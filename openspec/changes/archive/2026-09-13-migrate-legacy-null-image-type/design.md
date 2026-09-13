## Context

Legacy gscan2pdf 2.x configs (or `gscan2pdfrc` files re-imported by the
`fix-legacy-default-scan-options` migration on a clean start) store the document
type as JSON `null` (`"image type": null`). `_deserialise_and_migrate` runs
`_normalise_types`, whose `_coerce_str(None)` cannot produce a usable value, so
it leaves the setting as `None` and logs a WARNING. The raw `null` is then
re-emitted on every config write, so the warning persists on every startup even
after the user empties the rc file.

Current relevant code (`src/scantpaper/config.py`):

- `_read_config` → `_deserialise_and_migrate(config)` (line 320)
- `_normalise_types` (lines 99-117) and `_coerce_str` warn when a coercion
  yields `None`.
- Non-dict `default-scan-options` handling lives in the same module (the
  `fix-legacy-default-scan-options` migration) and serves as the precedent for
  fixing legacy shapes at load time.

## Goals / Non-Goals

**Goals:**
- Eliminate the startup WARNING caused by a legacy `null` image type.
- Make the stored value usable: migrate `None` to the application default
  `"pdf"` at load time.
- Stop re-emitting `null` on config writes so the warning cannot recur.

**Non-Goals:**
- Changing the image-type coercion behaviour in general (only the `null`
  legacy case is migrated).
- Touching `default-scan-options` (handled by the sibling migration) or any
  other setting.
- Introducing a new dependency.

## Decisions

### D1: Migrate at load time, not in the save dialog

The warning appears during `_read_config`, before any dialog exists. It is
therefore fixed in `config.py`, where `_deserialise_and_migrate` already runs.
During startup the rc file is NOT written back (writes only happen on quit), so
there is no risk of persisting the migrated value before the migration
completes.

Alternative (fix in `_normalise_types`, treating a coerced `None` as
"use default") was rejected: it would mask all uncoercible values, not just the
legacy `null`, and would hide genuinely broken user configs.

### D2: Normalise in `_deserialise_and_migrate` before type checking

The migration inserts a step: if `config.get("image type") is None`, set it to
`DEFAULTS["image type"]` ("pdf"). This runs before `_normalise_types`, so the
type normaliser sees a valid string and emits no warning meaningful to the user.

The same treatment applies to `default-scan-options` keys already handled by
`_normalise_scan_options` when present; no other `None`-valued settings are
affected.

### D3: Default value from `DEFAULTS`, not hard-coded

The migrated value comes from `DEFAULTS["image type"]` ("pdf") so it stays in
sync with the application default if that ever changes.

## Risks / Trade-offs

- A config where the user deliberately stored `null` image type intending "no
  type" is now treated as `"pdf"`; this matches the application default and the
  same behaviour scantpaper itself exhibits on a truly clean start, so there is
  no meaningful regression.
- The migration runs on every start for a legacy rc, but it is idempotent
  (once the value is "pdf", nothing changes) and the write-back at quit
  persists the migrated value, so it runs once in practice.
- Requires a config-delta spec and new tests; no API or dependency changes.
