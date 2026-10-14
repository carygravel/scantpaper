## ADDED Requirements

### Requirement: A slice can be rotated by 90 degrees

The editor SHALL provide controls to rotate a focused text slice 90 degrees
clockwise or anticlockwise. Rotating a slice SHALL change the angle at which
its text is drawn on the page (clockwise SHALL make the text run bottom-to-top,
anticlockwise SHALL make it run top-to-bottom), while keeping the slice's
bounding box rectangle axis-aligned. The rotation SHALL be persisted in the
page's text layer and SHALL be embedded in saved output.

#### Scenario: Rotating a slice clockwise
- **WHEN** the user focuses a text slice and activates the rotate-clockwise
  control
- **THEN** the slice's text SHALL be drawn rotated 90 degrees clockwise on the
  page
- **AND** the slice's bounding box SHALL remain axis-aligned
- **AND** the page's text layer SHALL record the rotation

#### Scenario: Rotating a slice anticlockwise
- **WHEN** the user focuses a text slice and activates the rotate-anticlockwise
  control
- **THEN** the slice's text SHALL be drawn rotated 90 degrees anticlockwise on
  the page
- **AND** the page's text layer SHALL record the rotation

#### Scenario: Rotation survives saving
- **WHEN** a slice has been rotated and the page is saved as a searchable PDF
- **THEN** the saved document SHALL render the slice's text at the rotated
  angle

### Requirement: New slices inherit the current rotation

A slice added while a rotation is set SHALL be created with that rotation, so
the user can author a run of vertical text without re-rotating each slice.

#### Scenario: Adding a slice with a rotation in effect
- **WHEN** the user has rotated the focused slice and then adds a new slice at
  a selection
- **THEN** the new slice SHALL be drawn at the same rotation
- **AND** the page's text layer SHALL record the new slice's rotation

### Requirement: The rotation controls act on the focused slice only

Rotating SHALL affect only the slice currently focused in the editor and SHALL
NOT change the rotation of any other slice.

#### Scenario: Rotating one slice leaves the others unchanged
- **WHEN** the user focuses one slice among several and rotates it
- **THEN** the other slices' text SHALL be drawn at their original angles
- **AND** the page's text layer SHALL keep the other slices' rotations
  unchanged
