# Proposal

## Why

With "Cache device list" enabled, scantpaper asks "Really cache libusb device
names?" on every start whenever any cached device name contains `libusb`. It
asks even when the cached list is merely being loaded and nothing new is being
written. A user whose device name is stable enough to cache - for example a
network scanner that embeds a libusb address but only renumbers when the server
reboots - is therefore asked the same question at every launch, and has no way
to answer it once.

## What Changes

- Ask the libusb caching question only when a freshly scanned device list is
  about to be stored in the cache. Loading an existing cached list into the
  scan dialog no longer triggers the question.
- Add a "Don't ask again" option to the question, persisted as a new setting.
  Chosen together with the affirmative answer, it means "cache libusb device
  names without asking", so later fresh scans are cached silently.
- Keep the existing "Cache device list" preference as the switch that enables
  or disables caching. Declining the question continues to disable caching,
  and suppression is recorded only for an affirmative answer, so re-enabling
  caching after a decline asks once more.
- Leave the failure path unchanged: opening a stale cached name still offers a
  rescan in the error dialog rather than rescanning automatically.

## Capabilities

### New Capabilities

- `device-list-caching`: how the SANE device list is cached and reused, and
  when the user is warned about caching volatile libusb device names.

### Modified Capabilities

- None.

## Impact

- `src/scantpaper/scan_menu_item_mixins.py`: the device-list callback
  distinguishes a fresh scan from a cache load before offering to cache, and
  the libusb confirmation honours the persisted suppression.
- `src/scantpaper/config.py`: one new boolean setting records the suppression
  (default: warn).
- `src/scantpaper/tests/test_scan_menu_item_mixins.py`: coverage for prompting
  on a fresh scan, staying silent on a cache load, and remembering an
  affirmative "don't ask again".
- Translations: updated template and seeded fuzzy entries for any new or
  changed user-visible strings.
- Documentation: README explains when the question appears and how to stop it.
- Not in scope: the inert "Cache device list" checkbox in the "Error opening
  the last device used" dialog, and automatic rescan-and-rematch after a failed
  open. Both are separate changes.
