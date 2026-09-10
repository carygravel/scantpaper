# Proposal: resilient-config-loading

## Why

A single malformed byte in `~/.config/scantpaperrc` (a hand-edited value, a
trailing comma, an encoding glitch) makes `read_config()` back up the whole
file and silently reset **every** setting to defaults. Users lose their entire
configuration (rotation, OCR, paper sizes, device settings) with no warning and
no recovery path — which looks exactly like a "settings don't save" bug (e.g.
`rotate facing: 90` / `rotate reverse: 270` in the file, but the GUI coming back
with defaults after restart).

## What Changes

- **Per-key rescue instead of wipe-and-revert**: when the rc file fails to parse
  as JSON, rescue as many valid settings as possible instead of discarding all
  of them. Currently `read_config` catches `JSONDecodeError`, renames the file to
  `scantpaperrc.old`, and returns an empty dict (config.py:169-173).
- **Keep and surface the backup**: retain the `*.old` backup, but do not treat a
  failed load as a valid reason to silently overwrite the file with defaults on
  the next quit. The next `write_config` must not clobber a broken-but-not-empty
  file without user awareness.
- **Notify the user**: report the failed load in the UI (message bar or dialog)
  instead of only via the log, so users know their settings were partially or
  fully reset and why.
- **Warn about broken values**: if the JSON parses but contains values of the
  wrong type (e.g. `"rotate facing": "90"`), keep the setting rather than
  silently defaulting it.

## Capabilities

### New Capabilities
- `config-loading`: robust reading of the user configuration file — parse
  failures rescue valid keys instead of wiping everything, backups are
  preserved, wrong-type values are normalised or kept, and the user is told
  when their config could not be read and what happened to it.

### Modified Capabilities
<!-- None: there is no existing spec covering config file I/O. -->

## Impact

- `src/scantpaper/config.py` — `read_config()` (recovery logic), and
  `write_config()` (guard against overwriting an unrescued/broken config).
- `src/scantpaper/app_window.py` — `_read_config()` reports failures to the UI
  instead of silently reverting.
- `src/scantpaper/tests/test_8_config.py` — existing tests for the
  revert-to-defaults path must be updated to the rescue behaviour.
- No external dependencies added. No changes to the rc file format: valid files
  round-trip exactly as before.