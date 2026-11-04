# device-blacklist Specification

## Purpose

Defines how users hide unwanted scan devices from the Device selector,
including how blacklist patterns match device information, how an empty
result is handled, and how a device is blacklisted from the dialog.

## Requirements

### Requirement: Blacklist patterns match what the user sees

The system SHALL treat the device blacklist value as a regular expression
and match it case-insensitively against each device's visible label and
its backend name, vendor, and model. Any device whose searched fields
match the pattern SHALL be omitted from the Device selector.

#### Scenario: Pattern matches the visible label

- **WHEN** the blacklist is `CameraA` and a device has the label
  `Noname CameraA: CameraA`
- **THEN** that device is omitted from the Device selector

#### Scenario: Pattern matches the backend name

- **WHEN** the blacklist is `v4l:.*` and a device has the backend name
  `v4l:/dev/video0`
- **THEN** that device is omitted from the Device selector

#### Scenario: Pattern does not match

- **WHEN** the blacklist is `CameraA` and a device has the label
  `EPSON Perfection V39`
- **THEN** that device remains in the Device selector

#### Scenario: Spaces in the pattern match literally

- **WHEN** the blacklist is `FaceTime HD Camera`
- **THEN** a device whose label contains that phrase with its spaces is
  omitted from the Device selector

### Requirement: Existing blacklist values keep working

A stored blacklist value that equals a device's backend name SHALL
continue to omit that device, so the corrected matching does not change
the meaning of values already saved in the configuration.

#### Scenario: Exact backend name remains effective

- **WHEN** the blacklist is `v4l:/dev/video0` and a device has that exact
  backend name
- **THEN** that device is omitted from the Device selector

### Requirement: Blacklisting every device does not fail

When filtering removes every device, the system SHALL report that no
devices were found, SHALL leave scanning unavailable, and SHALL NOT raise
an unhandled exception.

#### Scenario: All devices filtered out

- **WHEN** every returned device matches the blacklist
- **THEN** the user is told that no devices were found and no traceback
  occurs

### Requirement: Blacklist applies to cached device lists

When the scan dialog installs a cached device list, the system SHALL
apply the current blacklist to it, so a preference edit takes effect
without requiring a rescan.

#### Scenario: Cached device is blacklisted

- **WHEN** the device list is loaded from the cache and one cached entry
  matches the current blacklist
- **THEN** that entry is omitted from the Device selector

#### Scenario: Cache entirely blacklisted

- **WHEN** the cached device list is loaded and every entry matches the
  current blacklist
- **THEN** the no-devices outcome is shown without an unhandled exception

### Requirement: User can blacklist the selected device from the dialog

The Device selector SHALL offer a **Blacklist this device** action for
the currently selected device. The action SHALL append a pattern that
matches that device's visible label to the device blacklist, using
regular-expression escaping so the label is matched literally, and SHALL
remove the device from the selector. The action SHALL be unavailable when
no device is selected.

#### Scenario: Blacklist the selected device

- **WHEN** the user selects a device and activates **Blacklist this
  device**
- **THEN** a pattern matching that device is stored in the device
  blacklist and the device is removed from the Device selector

#### Scenario: Existing blacklist entries are preserved

- **WHEN** the blacklist already contains an entry and the user
  blacklists another device
- **THEN** both the existing entry and the new entry remain in the stored
  blacklist

#### Scenario: No device selected

- **WHEN** no device is selected in the Device selector
- **THEN** the **Blacklist this device** action is unavailable

### Requirement: Blacklist preference explains its match target

The device blacklist preference SHALL show a hint that the value is a
regular expression matched against the device label and name, including
an example value.

#### Scenario: User opens the preference

- **WHEN** the user views the device blacklist setting
- **THEN** the hint names the matched device information and gives an
  example pattern

### Requirement: Invalid blacklist patterns are rejected

When the user saves an invalid regular expression as the device
blacklist, the system SHALL show an error and SHALL keep the previously
stored value.

#### Scenario: Invalid pattern entered

- **WHEN** the user saves `[` as the device blacklist
- **THEN** an invalid-regex error is shown and the previous blacklist
  value is retained
