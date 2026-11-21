# context-menus Specification

## Purpose

Governs the right-click (secondary-button) context menus on the main
window's interactive surfaces — the image view and the thumbnail list — so
that a menu appears where the user clicks, on every GTK4 version, matching
the GTK3 behaviour. Owning the anchor behaviour separately from the menu's
contents keeps the two concerns (what the menu offers vs. where it appears)
independently evolvable.

## Requirements

### Requirement: Right-clicking an interactive surface shows its context menu

A secondary-button press on the image view SHALL show the image-view
context menu, and a secondary-button press on the thumbnail list SHALL show
the thumbnail-list context menu. A secondary-button press on any other main
window area SHALL NOT show a context menu.

#### Scenario: Secondary press on the image view

- **WHEN** the user right-clicks the image view
- **THEN** the image-view context menu is shown

#### Scenario: Secondary press on the thumbnail list

- **WHEN** the user right-clicks a row in the thumbnail list
- **THEN** the thumbnail-list context menu is shown

#### Scenario: Secondary press outside the surfaces

- **WHEN** the user right-clicks the main window area outside the image
  view and the thumbnail list
- **THEN** no context menu is shown

### Requirement: Context menu appears at the pointer

A context menu SHALL be displayed anchored at the pointer position of the
right-click that opened it, so the cursor lies at or immediately beside the
menu. It SHALL NOT be placed at a fixed or window-derived location that is
independent of the pointer.

#### Scenario: Menu at the click point

- **WHEN** the user right-clicks the image view at a point away from the
  window's corner
- **THEN** the context menu appears at that pointer position rather than at
  the top-left of the window

#### Scenario: Menu position tracks the click

- **WHEN** the user right-clicks the thumbnail list at two different rows
- **THEN** the context menu appears at the corresponding two different
  pointer positions

### Requirement: Context menu stays fully on-screen

A context menu SHALL be positioned so that it stays within the visible
screen, flipping or clamping its placement when the pointer is near a screen
edge, so no required menu item is unreachable by being cut off by the edge.

#### Scenario: Right-click near the bottom edge

- **WHEN** the user right-clicks near the bottom edge of the screen
- **THEN** the context menu is displayed shifted upward so it does not
  extend below the visible screen

#### Scenario: Right-click without a selection

- **WHEN** the user right-clicks the image view with no page or selection
- **THEN** a context menu is still shown and menu items whose actions need
  a selection are insensitive rather than hidden
