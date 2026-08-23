## Purpose

Ensure the application's toolbar icons are resolvable by the GTK icon theme in
every installation mode: source checkout, Python wheel, and distro package.

## ADDED Requirements

### Requirement: Icons resolve in a wheel install

When scantpaper is installed as a wheel, the application SHALL register its
bundled icons with the GTK icon theme such that all toolbar icons render,
without depending on any system path outside the installed package.

#### Scenario: Wheel-installed application shows icons
- **WHEN** scantpaper is installed as a Python wheel and the application
  initialises
- **THEN** the toolbar icons bundled inside the installed package are
  registered with the GTK icon theme
- **AND** toolbar buttons display their icons

#### Scenario: No access to system icon directories
- **WHEN** scantpaper runs from a wheel and `/usr/share/scantpaper/icons` is
  absent or unreadable
- **THEN** the bundled package icons are still registered and displayed

### Requirement: Icons resolve in a source checkout

When scantpaper runs from an uninstalled source checkout, the application SHALL
resolve the bundled icons so the developer/test workflow behaves identically to
a wheel install.

#### Scenario: Source checkout shows icons
- **WHEN** scantpaper is executed directly from the repository source tree
- **THEN** the icons in the package are registered with the GTK icon theme and
  toolbar icons are displayed

### Requirement: Distro install fallback

If the bundled package icons are not present, the application SHALL fall back to
the system icon path so distro-packaged installations (which may install icons
to a system theme) continue to work.

#### Scenario: Distro install falls back to system icons
- **WHEN** the bundled package icons are absent and a system icon path is
  configured
- **THEN** the system icon path is registered with the GTK icon theme
- **AND** toolbar icons are displayed

### Requirement: Icon path is install-mode independent

The icon discovery mechanism SHALL not depend on the relative location of a
source directory outside the installed package, so that moving or removing the
repository root does not break icon resolution in installed packages.

#### Scenario: Icons found via installed package resources
- **WHEN** scantpaper locates its icons at runtime
- **THEN** it resolves them from within the installed package resources rather
  than from a `../` path relative to the package directory
