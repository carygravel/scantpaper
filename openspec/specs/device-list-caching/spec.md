# device-list-caching Specification

## Purpose

Defines how scantpaper caches the SANE device list, reuses it when the scan
dialog opens, and warns the user before caching names that include `libusb`.

## Requirements

### Requirement: A usable cached list avoids the device search

When device-list caching is enabled, the stored list contains at least one
device that survives the blacklist, and no forced search was requested,
opening the scan dialog SHALL use the stored list without searching for
devices. When caching is disabled or the stored list is empty, scantpaper
SHALL search for devices.

#### Scenario: Opening the scan dialog with a usable cache

- **WHEN** the scan dialog opens with caching enabled and a non-blacklisted
  stored device
- **THEN** the dialog lists the stored devices without searching SANE

#### Scenario: Opening the scan dialog without a usable cache

- **WHEN** the scan dialog opens with caching disabled or with an empty stored
  list
- **THEN** scantpaper searches for devices before listing them

### Requirement: The libusb warning precedes only a non-cache list

When caching is enabled, scantpaper SHALL ask the libusb question only before
storing a device list that did not come from the cache and contains a device
whose name includes `libusb`. A device list loaded from the cache SHALL NOT
trigger the question.

#### Scenario: Starting from a cached list with libusb names

- **WHEN** the scan dialog loads a cached list that contains a `libusb` name
- **THEN** the question is not shown

#### Scenario: A new list contains libusb names

- **WHEN** a non-cache device list that contains a `libusb` name is about to
  be stored
- **THEN** scantpaper asks whether to cache it before storing

#### Scenario: A new list has no libusb names

- **WHEN** a non-cache device list contains no `libusb` name
- **THEN** scantpaper stores it without asking

### Requirement: Declining leaves the list uncached

Declining the libusb question SHALL leave the device list uncached and SHALL
disable device-list caching for later starts.

#### Scenario: User declines the question

- **WHEN** the libusb question is shown and the user declines
- **THEN** the new list is not stored and device-list caching is disabled

### Requirement: An affirmative answer can be remembered

The libusb question SHALL offer a "Don't ask again" choice. When the user
confirms caching with that choice selected, later device lists that would
otherwise trigger the question SHALL be cached without it, and the choice
SHALL persist across restarts. Confirming without the choice SHALL ask again
the next time such a list is cached.

#### Scenario: Confirming with "Don't ask again"

- **WHEN** the user confirms caching and selects "Don't ask again"
- **THEN** the list is cached and later `libusb` lists are cached silently

#### Scenario: Confirming without "Don't ask again"

- **WHEN** the user confirms caching without selecting "Don't ask again"
- **THEN** the list is cached and the next `libusb` list asks again

#### Scenario: Declining does not remember suppression

- **WHEN** the user declines the question with "Don't ask again" selected
- **THEN** no suppression is recorded, and enabling caching again asks before
  storing a `libusb` list

### Requirement: Confirmed lists replace the cache

When the user confirms caching, scantpaper SHALL store the list that was
offered, replacing any list cached before.

#### Scenario: Caching a list after the device name changed

- **WHEN** a new list with a changed `libusb` address is confirmed for caching
- **THEN** the new address is stored and used on the next start
