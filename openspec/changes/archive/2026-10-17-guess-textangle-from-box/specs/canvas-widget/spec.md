## ADDED Requirements

### Requirement: Canvas fits slice text along the correct axis

The Canvas SHALL choose the axis that rendered slice text spans from the
slice's drawn angle: a slice drawn at 0 or 180 degrees SHALL scale its text to
span the slice's width, and a slice drawn at 90 or 270 degrees SHALL scale its
text to span the slice's height. This SHALL hold whether the drawn angle comes
from the slice's own text angle or from an ancestor's accumulated angle.

#### Scenario: A 180-degree slice is sized like an upright slice

- **WHEN** two slices carry the same text and the same bounding-box width and
  height, one drawn at 0 degrees and the other at 180 degrees
- **THEN** the text of the 180-degree slice SHALL be drawn at the same size as
  the text of the upright slice
- **AND** it SHALL NOT be shrunk to the slice's height

#### Scenario: A 90-degree slice spans its height

- **WHEN** a slice is drawn at 90 degrees in a bounding box taller than it is
  wide
- **THEN** its text SHALL be drawn spanning the slice's height

#### Scenario: An inherited 180-degree angle selects the width

- **WHEN** a slice with no text angle of its own is drawn at 180 degrees because
  of an ancestor's accumulated angle
- **THEN** its text SHALL be drawn spanning the slice's width
