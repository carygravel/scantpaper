## ADDED Requirements

### Requirement: Menu bar loads on the supported toolkit floor

The main window SHALL load its in-window menu bar from the shipped UI
definition on every supported GTK 4 version, including GTK 4.6. The loaded
menu SHALL expose the same top-level menus and action links as on newer GTK
versions.

#### Scenario: Menu bar loads on GTK 4.6

- **WHEN** the main window is constructed with GTK 4.6
- **THEN** the UI definition SHALL load without an error
- **AND** the menu bar SHALL show File, Edit, View, Tools and Help

#### Scenario: Menu actions survive the compatible definition

- **WHEN** the menu bar is loaded on GTK 4.6 or newer
- **THEN** opening File SHALL show its items
- **AND** activating New SHALL invoke the same action as on newer versions
