# Design

## Context

See `proposal.md - Why`. The 1-bit-request test lives in `_depth_mismatch`
(`src/scantpaper/dialog/sane.py:670`), which decides "was 1-bit output
requested?" by reading `self.current_scan_options`, a `Profile` that records
only options **explicitly set** through the dialog (see `scanner/profile.py`
and `add_backend_option`). A backend whose *default* mode is bilevel (e.g.
Lineart on the fujitsu backend) never appears there unless the user touches
the mode, so `_depth_mismatch` returns False, the delivered 8-bit frame is
left as grayscale, and Automatic compression saves an 8-bit Flate image.

`scan()` (`dialog/sane.py:564`) already reads live backend option values at
batch start via `_get_xy_resolution` (`scan.py:1587`, which calls
`thread.get_option_value`); the worker is idle at that point, so a blocking
read is safe there.

## Goals / Non-Goals

**Goals:**

- Decide "was 1-bit requested?" from the scanner's **effective** mode/depth,
  including a backend default the user never touched.
- Keep the decision stable for a whole batch without blocking reads mid-scan.

**Non-Goals:**

- Predicting backend behaviour before scanning (detection stays post-snap).
- Changing the colour-aware threshold conversion itself.
- Touching the profile save/load semantics or the `changed-current-scan-options`
  signal.

## Decisions

### Read the effective mode and depth at batch start, not from the profile

At the top of `scan()`, alongside `_get_xy_resolution()`, capture the
effective values of the `depth` and `mode` options via `thread.get_option_value`
(the same mechanism resolution uses). Thread these two values into
`new_page_callback` and `_depth_mismatch`, which then test:

```
delivered == "1"              -> no conversion (already 1-bit)
effective depth == 1          -> convert
effective mode is bilevel     -> convert   (via existing _BILEVEL_MODE_RE)
otherwise                     -> no conversion
```

This is correct in both reported cases: the default-Lineart backend reports
`mode="Lineart"` even before any explicit set, and an explicit Color→Lineart
switch reports the same. Since scan options are fixed for a batch, capturing
once at start gives a stable decision and avoids a blocking read inside
`new_page_callback` while the worker is transferring a frame.

- Alternative: keep reading `current_scan_options` and seed it with backend
  defaults at option-load. Rejected: changes the meaning of the profile from
  "explicit sets" to "effective state", rippling into profile saving, the
  `changed-current-scan-options` signal, and `set_current_scan_options`'s
  "empty profile -> apply defaults" shortcut.
- Alternative: call `get_option_value` inside `_depth_mismatch` per page.
  Rejected: `new_page_callback` runs on the main thread while the worker is
  mid-batch; a blocking read there can stall page delivery.

### Missing or inactive mode/depth options stay a safe default

`get_option_value` may raise or return `None` when the option does not exist
or is inactive (e.g. a backend with no `depth` option). Treat either axis as
"not requested" in that case - the same conservative default the current code
uses when the profile has no entry - so a scanner with only continuous-tone
modes never triggers a conversion. The existing `_BILEVEL_MODE_RE` matching is
reused unchanged.

### Single source of truth for the test remains the delivered image

The delivered PIL mode stays authoritative for the "was a deeper frame
delivered?" half of the test (`delivered == "1"` short-circuits), matching the
original design's finding that python-sane never returns mode-"1" frames for
3-sample/grayscale data. Only the *request* half moves from the profile to the
effective backend value.

## Risks / Trade-offs

- [Reading `get_option_value` at scan start adds a small latency before the
  first page] → Negligible; resolution is already read the same way, and it
  happens once per batch.
- [A backend reports an effective mode the dialog did not surface] → The
  bilevel match is conservative (full-value, whitelist from backend docs); an
  unknown/continuous-tone value means no conversion, preserving today's safe
  default.
- [Switching the request source invalidates the existing test that seeds
  mode/depth via the profile] → The `test_new_scan_enforce_depth` table and
  mocks are adapted so `get_option_value` answers for mode/depth, and a case
  for a backend-default bilevel mode (nothing explicitly set) is added.

## Migration Plan

Single-commit change; no configuration or data migration. Rollback is
reverting the request source in `_depth_mismatch` and `scan()`.

## Open Questions

(none)
