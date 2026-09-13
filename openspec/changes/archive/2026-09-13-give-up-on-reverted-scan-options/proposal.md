## Why

When a scan profile asks the backend to set scan options that are coupled to
the same underlying state (e.g. the Epson GT-20000's aliased `quick-format`
and `scan-area`, or a media size that also drives the numeric `tl/br`
geometry), the backend reverts an option every time a sibling is set. The
apply loop then re-applies the reverted value, which reverts its sibling, and
so on. The current safety net is a single global counter that only trips after
`n·(n+1)/2` reloads (2278 for a 67-option device, ~15s of spinner on this
Epson), and then abandons the whole apply with a generic "file a bug report"
dialog and no clue which option is fighting the backend.

## What Changes

- Track how often each scan option is **re-applied after being reverted by a
  reload**, instead of a single global reload count.
- Give up on a specific option once it has been reverted a small fixed number
  of times (K=2): stop re-applying it for the rest of that apply pass, drop it
  from `current_scan_options` so it is not re-applied or re-saved, log which
  option was dropped and why, and continue applying the remaining options
  ("last writer wins").
- Keep a linear, option-count-based total reload cap as a backstop so a
  hostile backend still cannot hang the dialog.
- Reset both counters at the start of each profile apply (they currently only
  reset on user widget interaction, so unrelated applies accumulate toward the
  same budget).
- User-visible behaviour change: opening the scan dialog with a
  non-converging saved profile now settles in a fraction of a second, requires
  no user intervention, makes the saved defaults self-heal, and logs the
  offending option instead of showing the "Reload recursion limit exceeded"
  error.

## Capabilities

### New Capabilities

- `scan-option-convergence`: Guarantees that applying scan options from a
  profile terminates, even when the backend couples or aliases options, by
  per-option revert detection, a linear total-reload backstop, and resetting
  the counters per apply pass.

### Modified Capabilities

(none)

## Impact

- `src/scantpaper/dialog/scan.py`: `_update_options` reload-accounting and
  the `reload_recursion_limit`/`num_reloads` logic; profile application
  (`_set_option_profile`, `_set_option_with_hook`) to carry per-option state;
  `current_scan_options` dropping of a reverted option.
- `src/scantpaper/dialog/sane.py`: reset points for the counters and any
  set-option callbacks that feed revert detection.
- Existing tests: `test_0608_dialog_scan.py::test_infinite_reloads` and
  related recursion-limit tests will need updating to the new semantics; new
  tests for the coupled-options scenario (the Epson GT-20000 log reproduced
  with mocks).
- No new dependencies, no config/database changes.