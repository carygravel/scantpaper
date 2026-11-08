# icon-only-buttons Specification

## Purpose

Buttons whose only visible content is an icon stay understandable and
accessible: each can be identified by sight, by keyboard and by assistive
technology, and none is allowed to render a missing-image placeholder.

## Requirements

### Requirement: Icon-only buttons have an accessible name

Every button whose only visible content is an icon SHALL expose a non-empty
accessible name that states the button's action.

#### Scenario: Screen reader announces the profile buttons

- **WHEN** a screen reader focuses the Save, Edit or Delete button in the Scan
  profiles frame
- **THEN** it announces that button's action rather than only "button"

#### Scenario: Every audited icon-only button has a name

- **WHEN** the scan dialog, the paper-size editor, the profile editor,
  Preferences or the Save dialog is shown
- **THEN** every icon-only button in it exposes a non-empty accessible name

### Requirement: Icon-only buttons explain themselves on hover

Every button whose only visible content is an icon SHALL have a tooltip that
describes its action, unless the button shows a visible text label instead.

#### Scenario: Hovering the profile buttons

- **WHEN** the pointer rests over the Save, Edit or Delete button in the Scan
  profiles frame
- **THEN** a tooltip describes the action that button performs

#### Scenario: A labelled button is already identifiable

- **WHEN** a button shows a visible text label beside its icon
- **THEN** it does not need a tooltip to explain its action

### Requirement: Button icons resolve in the active theme

Every icon name used by an icon-only button SHALL resolve to an icon, from the
application's bundled icons or from the active icon theme, so the button never
shows the missing-image placeholder.

#### Scenario: The profile Edit button shows an edit icon

- **WHEN** the Scan profiles frame is shown
- **THEN** its Edit button displays a real edit icon and not the missing-image
  placeholder

#### Scenario: Every audited button icon resolves

- **WHEN** the application runs with the desktop's icon theme
- **THEN** every audited icon-only button displays the icon its action
  requires, and none displays the missing-image placeholder
