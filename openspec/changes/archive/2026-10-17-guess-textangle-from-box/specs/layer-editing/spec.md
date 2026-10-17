## ADDED Requirements

### Requirement: A new slice's orientation is guessed from its selection

When a slice is added, duplicated, or first created on a page that has no text
layer, and it inherits no quarter-turn rotation, the editor SHALL choose the
slice's text angle as the orientation in which the slice's text is drawn at the
largest size that fits the selected rectangle. The angle SHALL be 0 degrees
when the text fits upright at least as well as rotated, and 90 degrees when the
rotated fit is larger. A guessed angle SHALL be an ordinary text angle: it SHALL
be drawn, persisted in the page's layer, serialised in saved output, and remain
correctable with the rotate controls. When a quarter-turn rotation is already
inherited from the focused slice or an ancestor, the editor SHALL use that
rotation and SHALL NOT guess.

#### Scenario: A tall selection for vertical text is created rotated

- **WHEN** the user draws a selection taller than it is wide and adds a text
  whose upright rendering would be smaller than its rotated rendering in that
  selection
- **THEN** the new slice SHALL be created with a text angle of 90 degrees
- **AND** its text SHALL be drawn at the larger, rotated size spanning the
  selection's height
- **AND** the page's text layer SHALL record the 90-degree angle

#### Scenario: A wide selection is created upright

- **WHEN** the user draws a selection wider than it is tall and adds a text
  whose upright rendering fits at least as well as its rotated rendering
- **THEN** the new slice SHALL be created with a text angle of 0 degrees
- **AND** its text SHALL be drawn upright spanning the selection's width

#### Scenario: A short text in a slightly tall selection stays upright

- **WHEN** the user draws a selection only slightly taller than it is wide and
  adds a short text that fits the selection's width upright
- **THEN** the new slice SHALL be created with a text angle of 0 degrees

#### Scenario: Duplicating a slice guesses the same orientation

- **WHEN** the user activates the duplicate control on a tall selection whose
  text would be larger rotated
- **THEN** the duplicate SHALL be created with a 90-degree text angle
- **AND** the focused slice SHALL remain unchanged

#### Scenario: A first slice on a page with no layer is guessed too

- **WHEN** the page has no text layer, the user draws a tall selection, and
  activates the add control
- **THEN** the page SHALL gain a text layer whose first slice carries the
  guessed 90-degree angle

#### Scenario: An inherited rotation is not overridden by the guess

- **WHEN** the focused slice carries a 90-degree rotation and the user adds a
  new slice at a selection
- **THEN** the new slice SHALL be drawn at the inherited 90-degree rotation
- **AND** the geometry guess SHALL NOT add a further quarter turn

#### Scenario: A guessed rotation is correctable

- **WHEN** a slice created with a guessed rotation is focused and the user
  activates a rotate control
- **THEN** the slice's text angle SHALL change by that quarter turn
- **AND** the change SHALL be persisted in the page's text layer
