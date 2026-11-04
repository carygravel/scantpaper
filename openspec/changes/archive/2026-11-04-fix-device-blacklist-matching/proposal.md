# Proposal

## Why

The "Device blacklist" preference does not work as advertised: a SANE
backend that offers a camera as a scanner cannot be hidden. The current
code passes the device identifier as the regular-expression *pattern* and
the user's blacklist as the *text being searched*, so a user pattern such
as `CameraA` or `hp.*` can never match. It also matches only the invisible
SANE name (`v4l:/dev/video0`) rather than the label shown in the Device
dropdown, and it applies `re.VERBOSE`, which silently ignores spaces in
the user's text. Finally, filtering out every device would make
`_changed_device_list_callback` index an empty list and crash.

## What Changes

- Evaluate the blacklist entry **as the regular expression** and match it
  against the visible device label plus the backend name, vendor, and
  model, case-insensitively. Plain substrings such as `CameraA` work, and
  spaces match literally (drop `re.VERBOSE`/`re.DOTALL`).
- Keep backwards compatibility: a stored blacklist that is the exact SANE
  name continues to match because the name remains in the searched text.
- Handle an empty result after filtering: show the existing "No devices
  found" error instead of crashing, and leave the scan action disabled.
- Re-apply the blacklist when a cached device list is installed, so editing
  the preference takes effect on the next scan dialog without a rescan.
- Add a **Blacklist this device** action to the Device selector that appends
  a safely escaped pattern for the currently selected device to the
  preference. The text entry stays available for advanced patterns.
- Document the match target in the preference tooltip and entry
  placeholder, with an example, so the value is discoverable without
  reading the source (this folds the "explain the target" fix into the
  UI text).
- Cover the corrected behaviour with tests that distinguish the argument
  order, including a pattern different from the device name, a label
  containing spaces, the empty-result path, the cached-list path, and the
  one-click action.

Not a breaking change: existing stored values keep their previous matches,
and the preference format is unchanged.

## Capabilities

### New Capabilities

- `device-blacklist`: how scan devices are filtered out of the Device
  selector, how the blacklist pattern is matched and validated, how an
  empty filtered list is handled, and how the user blacklists the
  currently selected device from the dialog.

### Modified Capabilities

None. No existing requirement covers device blacklisting; the
`scan-device-selection` capability only governs the selector's placement.

## Impact

- `src/scantpaper/scan_menu_item_mixins.py`: corrected pattern matching,
  empty-list guard, cached-list filtering.
- `src/scantpaper/dialog/scan.py`: the "Blacklist this device" action and
  its wiring to the current device.
- `src/scantpaper/dialog/preferences.py`: tooltip and entry placeholder.
- `src/scantpaper/edit_menu_mixins.py`: preference validation remains, now
  consistent with the matcher.
- Tests under `src/scantpaper/tests/` for the matcher, dialog callback,
  cached path, and action.
- `README.md` and the translation template (`dev/generate_pot.py`) for the
  user-visible tooltip, placeholder, and action label.
