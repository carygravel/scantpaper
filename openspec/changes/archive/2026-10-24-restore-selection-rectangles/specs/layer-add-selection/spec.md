## ADDED Requirements

### Requirement: The image view paints the shared selection visibly

When the shared selection is set, the image view SHALL paint the selection
rectangle with the application's `.rubberband` style class, so the selection
is visible on the Image tab. The paint SHALL follow the GTK CSS cascade, so a
user-provided `.rubberband` rule in the user's gtk.css overrides the
application default.

#### Scenario: Shared selection is visible in the image view

- **WHEN** the user draws a selection in the image view or a layer pane so
  that the shared selection is set
- **AND** the application's stylesheets are installed
- **THEN** the Image tab SHALL paint a visible rectangle at the selection's
  widget coordinates using the application's `.rubberband` style

#### Scenario: User stylesheet recolours the image-view selection

- **WHEN** the user provides a `.rubberband` rule in their gtk.css with a
  background colour distinct from the application default
- **AND** a shared selection is set
- **THEN** the Image tab SHALL paint the selection with the user's colour
  instead of the application default
