# main-menu Specification

## Purpose
The main window presents the application's menu structure itself, so that
every action is discoverable on any desktop, without depending on the desktop
shell to render an exported menu model.
## Requirements
### Requirement: Main window shows the application menus in-window

The main window SHALL present the application's menu structure inside the
window on every desktop environment, rather than relying on a desktop shell
to render an exported menu model.

#### Scenario: Menus are visible at startup

- **WHEN** the application starts, on any desktop environment
- **THEN** the main window shows the application's top-level menus
  (File, Edit, View, Tools, Help)

#### Scenario: Opening a menu shows its items

- **WHEN** the user opens a top-level menu
- **THEN** its menu items are shown and activating one performs the
  corresponding action

#### Scenario: No desktop-shell integration is required

- **WHEN** the desktop environment does not render exported application
  menu models
- **THEN** the menus are still shown in the main window

### Requirement: Menus reflect action availability

Every menu item SHALL be insensitive while its action is disabled and
sensitive while it is enabled, so that the menu state matches what the user
can actually do.

#### Scenario: Page-dependent items are insensitive without a selection

- **WHEN** no page is selected
- **THEN** menu items whose actions require a selected page are insensitive

#### Scenario: Items become sensitive once a page is selected

- **WHEN** a page is selected
- **THEN** those menu items become sensitive

### Requirement: Keyboard shortcuts remain available

Actions reachable from the menus SHALL also remain reachable through their
keyboard shortcuts, independently of whether a menu is open.

#### Scenario: Shortcut activates an action

- **WHEN** the user presses a shortcut registered for a menu action
- **THEN** the action runs

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

