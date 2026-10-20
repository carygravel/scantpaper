# Platform Compatibility

## Purpose

Defines the oldest Linux distribution and toolkit versions that a released
scantpaper build must run on, so packaging and CI do not silently drift onto
newer APIs while jammy is still supported.

## Requirements

### Requirement: Supported platform floor

Released builds SHALL run with Python 3.10, GTK 4.6 and PyGObject 3.42, the
versions provided by Ubuntu 22.04 (jammy). Jammy SHALL remain supported until
2027-06. Ubuntu 24.04 (noble), Debian and newer toolchains SHALL also remain
supported.

The application and its test suite SHALL use only GTK and PyGObject APIs
available at that floor. An API introduced after the floor MAY be used only
when the application detects its availability at runtime and has a working
fallback for older versions.

#### Scenario: Application starts on jammy

- **WHEN** scantpaper is started on Ubuntu 22.04 with GTK 4.6.9 and
  PyGObject 3.42.1
- **THEN** the main window SHALL open with its menu bar and page view
- **AND** no GtkBuilder or missing-method error SHALL prevent startup

#### Scenario: Test suite passes on both LTS runners

- **WHEN** the test suite runs on Ubuntu 22.04 and Ubuntu 24.04
- **THEN** every test SHALL pass on both runners without skips for missing
  toolkit APIs

#### Scenario: Newer API is used only with a fallback

- **WHEN** a code path uses a GTK or PyGObject API newer than the supported
  floor
- **THEN** the path SHALL check for that API at runtime
- **AND** it SHALL use a supported alternative when the API is absent

### Requirement: Thumbnail stylesheet loads at the toolkit floor

The thumbnail stylesheet SHALL be loaded with a `Gtk.CssProvider` method that
exists on GTK 4.6, and the application SHALL keep the rule that pins the
thumbnail icon size to the generated pixbuf size. The test suite SHALL verify
the installed rule without using a PyGObject binding that crashes at the floor.

#### Scenario: Thumbnail rule is installed on jammy

- **WHEN** the thumbnail list is prepared on GTK 4.6.9 and PyGObject 3.42.1
- **THEN** the stylesheet SHALL load through `load_from_data`
- **AND** the provider SHALL report the 100px `-gtk-icon-size` rule
- **AND** the test SHALL NOT call `Gtk.Widget.snapshot_child` when PyGObject
  cannot marshal `Gtk.Snapshot` safely

#### Scenario: Painted thumbnail is checked on newer PyGObject

- **WHEN** the test runs on PyGObject 3.48.2 or newer
- **THEN** it SHALL also inspect the render tree and assert a thumbnail is
  painted at its generated size

### Requirement: Fractional spin buttons commit at the toolkit floor

Fractional spin buttons SHALL commit their entry value when the user presses
Return or Enter, including on GTK 4.6 where the `Gtk.SpinButton::activate`
signal does not exist.

#### Scenario: Enter commits a fractional value on jammy

- **WHEN** the user types a fractional value in a preferences, unpaper or scan
  spin button on GTK 4.6.9 and PyGObject 3.42.1
- **THEN** pressing Return or KP_Enter SHALL invoke the validation callback
- **AND** the value SHALL be applied without an `activate` signal connection

#### Scenario: Enter commits a fractional value on noble

- **WHEN** the same operation is performed on GTK 4.14.5 and PyGObject 3.48.2
- **THEN** the key controller SHALL provide the same commit behaviour

### Requirement: Release procedure records the support window

The release procedure SHALL state the jammy support end date and the
GTK/PyGObject versions that define the compatibility floor, so dropping jammy
is a deliberate release decision rather than an accidental consequence of an
API upgrade.

#### Scenario: Floor is visible to a releaser

- **WHEN** a maintainer follows the release procedure
- **THEN** the procedure SHALL name jammy's end date and the oldest supported
  GTK and PyGObject versions
