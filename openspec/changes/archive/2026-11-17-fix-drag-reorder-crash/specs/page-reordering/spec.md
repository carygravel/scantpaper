# Spec Delta

## ADDED Requirements

### Requirement: Reorder drag must not crash the process
A drag-and-drop page reorder interaction SHALL never terminate the
application with a native fault, from the moment the user starts dragging a
page row until the reorder operation completes, on every supported toolkit
version, display server and release combination.

#### Scenario: Starting a page drag
- **WHEN** the user presses and begins to move a page row in the thumbnail
  list
- **THEN** the application SHALL continue running without a native fault
- **AND** a reorder drag SHALL begin

#### Scenario: Dragging over the page list
- **WHEN** the pointer moves across other page rows while a reorder drag is
  in progress
- **THEN** the application SHALL continue running without a native fault
- **AND** the drag SHALL remain active through the movement

#### Scenario: Dropping a page on a new position
- **WHEN** the user releases the drag over a target page row
- **THEN** the application SHALL continue running without a native fault
- **AND** the pages SHALL be reordered to the drop position as a single
  undoable operation

#### Scenario: Reorder drags at the toolkit floor and on current releases
- **WHEN** reorder drags are performed on GTK 4.6 (Ubuntu 22.04 jammy), on
  current GTK releases, and on both X11 and Wayland sessions
- **THEN** the interaction SHALL complete without a native fault on every
  supported combination
