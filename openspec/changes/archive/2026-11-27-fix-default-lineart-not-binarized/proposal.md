# Proposal

## Why

When a scanner's default scan mode is bilevel (e.g. Lineart on the Fujitsu
ScanSnap S1500 / fujitsu backend) and the user starts scanning without
changing the mode in the scan dialog, the delivered page is stored as 8-bit
grayscale (format `L`) instead of 1-bit. The page is only binarized after the
user has explicitly switched the mode away from and back to a bilevel value.
As a result, saving with Automatic compression produces a larger 8-bit Flate
image (162K) instead of the expected 1-bit CCITT G4 (63K).

## What Changes

- The depth-mismatch decision (was 1-bit output requested?) will be evaluated
  against the scanner's **effective** scan mode and depth - including the
  backend's own default value - rather than only the set of options the user
  explicitly changed through the scan dialog.
- A scan whose effective mode is bilevel, or whose effective depth is 1 bit,
  will be converted to 1-bit even when the user did not explicitly touch the
  mode/depth controls.
- The existing warning and non-blocking progress notice continue to inform the
  user whenever a deeper frame is converted. No conversion is made when the
  effective mode/depth is continuous-tone (grayscale or colour).
- The effective mode/depth is captured once per batch at scan start (the same
  safe point where resolution is already read), so the decision is stable for
  the whole batch and does not require a blocking read mid-scan.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sane-page-acquisition`: "1-bit output is requested" is split into its own
  requirement so that the request is determined by the effective scan
  mode/depth (including backend defaults), not only by options the user
  explicitly set. A bilevel default that the user leaves untouched is now
  treated as a 1-bit request; an effective depth of 1 bit takes precedence
  over a continuous-tone mode. The "Requested colour depth is honoured"
  requirement keeps the conversion semantics, and an effective continuous-tone
  mode still leaves deeper frames untouched.

## Impact

- `src/scantpaper/dialog/sane.py`: `_depth_mismatch` and `scan()` - the 1-bit
  request test moves from the explicit-options profile to the effective
  backend mode/depth captured at batch start.
- `src/scantpaper/tests/test_0610_dialog_scan_sane.py`: the
  `test_new_scan_enforce_depth` table and mocks that feed mode/depth through
  the profile will be adapted to the effective-value source, and a case for a
  backend-default bilevel mode will be added.
- No user-visible UI, dependency, or data-model change; no migration.
