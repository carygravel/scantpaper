## ADDED Requirements

### Requirement: Canvas selection rectangle is visibly painted and themeable

The Canvas SHALL paint its selection rectangle using the application's
`.rubberband` style class, so the rectangle is visible on screen rather than
transparent. The painted style SHALL come from the application's stylesheets
through the normal GTK CSS cascade, so a user-provided `.rubberband` rule in
the user's gtk.css SHALL override the application's default.

#### Scenario: Selection renders as visible pixels

- **WHEN** the canvas knows the extent of the displayed page and has a
  selection
- **AND** the application's stylesheets are installed
- **THEN** rendering the canvas SHALL paint pixels within the selection's
  widget bounds whose colour differs from the surrounding scene
- **AND** those pixels SHALL match the application's default `.rubberband`
  style

#### Scenario: User stylesheet overrides the selection colour

- **WHEN** the user provides a `.rubberband` rule in their gtk.css with a
  background colour distinct from the application default
- **AND** the canvas has a selection
- **THEN** the canvas SHALL paint the selection with the user's colour
  instead of the application default
