## Why

`dev/check_launchpad.py` tells the maintainer when **upstream** has moved (new
translations, a changed template) and the catalogs should be pulled down. It
says nothing about the reverse direction: when the **local source** has gained
new or changed strings since the last pot was uploaded to Launchpad, so the pot
on Launchpad is out of date and a new one should be pushed up. That gap is
currently judged by eye, and it can drift silently between releases.

## What Changes

- Extend `dev/check_launchpad.py` to also report **local pot staleness**: the
  freshly generated message set is compared against a record of the last pot
  uploaded to Launchpad, and a difference is reported as "regenerate and
  upload a new pot".
- Extend the committed baseline `po/launchpad-state.json` with the fingerprint
  of the last uploaded pot, so the two directions share one snapshot.
- Add an explicit option to stamp the baseline after a pot has actually been
  uploaded, mirroring the existing `--update` behaviour.
- Add a `local_pot_changed` signal to the JSON report and make the scheduled
  `translations-check` workflow file a "new strings ready to upload" issue, so
  drift is caught automatically rather than at release time.
- Update `release_procedure.md` to record the new upload step.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `translations`: add a requirement covering detection of a stale local message
  template against a recorded baseline (the reverse of the existing upstream
  change detection).

## Impact

- `dev/check_launchpad.py`: new fingerprint extraction, a `local_pot_changed`
  report signal, and a stamp-after-upload option; shared HTTP/CLI conventions
  reused.
- `po/launchpad-state.json`: schema gains an `uploaded_pot` section.
- `.github/workflows/translations-check.yml`: also regenerate the pot and file
  an issue when the local message set has moved.
- `release_procedure.md`: document the new check/stamp step.
- Tests in `src/scantpaper/tests` covering the new signal and fingerprint.
- No new Python dependencies (standard library only, as today).
