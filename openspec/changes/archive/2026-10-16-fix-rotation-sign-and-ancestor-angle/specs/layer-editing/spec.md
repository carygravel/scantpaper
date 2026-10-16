## MODIFIED Requirements

### Requirement: A slice can be rotated by 90 degrees

The editor SHALL provide controls to rotate a focused text slice 90 degrees
clockwise or anticlockwise. Rotating a slice SHALL change the angle at which
its text is drawn on the page (clockwise SHALL make the text run top-to-bottom,
anticlockwise SHALL make it run bottom-to-top), while keeping the slice's
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
the user can author a run of vertical text without re-rotating each slice. The
new slice SHALL be drawn at the same angle as the focused slice, regardless of
where in the slice hierarchy it is inserted.

#### Scenario: Adding a slice with a rotation in effect
- **WHEN** the user has rotated the focused slice and then adds a new slice at
  a selection
- **THEN** the new slice SHALL be drawn at the same rotation as the focused
  slice
- **AND** the page's text layer SHALL record the new slice's rotation

#### Scenario: Adding a slice when the focused slice is its own parent

- **WHEN** the user focuses a slice that already carries a rotation and the new
  slice is inserted as a child of that same slice
- **THEN** the new slice SHALL be drawn at the same angle as the focused slice
- **AND** that angle SHALL NOT be applied twice

## ADDED Requirements

### Requirement: A slice's rotation composes with its ancestors' rotation

A slice's drawn angle SHALL be its own text angle plus the accumulated text
angle of all of its ancestors, at every nesting depth. A rotation carried by an
ancestor SHALL therefore rotate every slice beneath it by the same amount, and
the rotation SHALL be applied exactly once.

#### Scenario: A rotated ancestor rotates its descendants

- **WHEN** a page, region or line carries a text angle and its descendants carry
  no text angle of their own
- **THEN** every descendant slice SHALL be drawn rotated by the ancestor's angle
- **AND** the ancestor's rotation SHALL be applied at every depth, not only to
  its immediate children

#### Scenario: Nested rotations accumulate

- **WHEN** a slice and an ancestor of that slice each carry a text angle
- **THEN** the slice SHALL be drawn at the sum of its own angle and the
  ancestor's angle

#### Scenario: An unrotated document is unchanged

- **WHEN** neither a slice nor any of its ancestors carries a text angle
- **THEN** the slice SHALL be drawn unrotated
