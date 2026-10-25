# Layer Editing

## Purpose

Let the user correct, add, duplicate and delete individual OCR text slices and
annotation notes over a scanned page, and make every one of those edits visible
both on the page and in the document that is eventually saved.

## Requirements

### Requirement: Focusing a slice shows its current text

When the editor takes focus on a text slice, the editing control SHALL display
the text of that slice.

#### Scenario: Focusing a slice by clicking it
- **WHEN** the user clicks a text slice on the page
- **THEN** the control SHALL display that slice's current text
- **AND** the slice's bounding box SHALL be selected on the page

#### Scenario: Focusing a slice with the navigation controls
- **WHEN** the user activates the control to go to the least confident text
- **THEN** the control SHALL display the text of the least confident slice
- **AND** subsequent activations of the previous/next controls SHALL move
  through slices without leaving the control empty

### Requirement: Accepting a correction writes it to the page's layer

Accepting a correction SHALL write the edited text and the current selection
rectangle into the page's layer, and SHALL mark the slice as fully confident.

#### Scenario: Correcting a slice's text
- **WHEN** the control shows "helo" and the user replaces it with "hello" and
  accepts
- **THEN** the page's text layer SHALL contain "hello" for that slice
- **AND** the slice's confidence SHALL be 100
- **AND** the layer SHALL be persisted so it survives leaving the page

#### Scenario: Accepting moves the selection to the corrected rectangle
- **WHEN** the user drags the selection rectangle and accepts
- **THEN** the slice's bounding box in the page's text layer SHALL match the new
  selection

### Requirement: A correction is shown on the page immediately

Accepting a correction SHALL redraw the page so that the text drawn over the
image matches the text that will be saved.

#### Scenario: Corrected glyphs replace the previous ones
- **WHEN** a slice showing "helo" is corrected to "hello" and accepted
- **THEN** the text drawn over the page SHALL read "hello"
- **AND** it SHALL no longer read "helo"

#### Scenario: Confidence colour updates with the text
- **WHEN** a low-confidence slice is corrected and accepted
- **THEN** both its outline and its text SHALL be redrawn in the colour
  corresponding to full confidence

### Requirement: Deleting a slice removes it from the page's layer

Deleting a slice SHALL remove it from the page's layer, so that it is no longer
drawn on the page and no longer appears in the text that is embedded in saved
output.

#### Scenario: Deleted text is absent from saved output
- **WHEN** a slice containing "DELETE-ME" is deleted
- **AND** the page is saved as a searchable PDF
- **THEN** "DELETE-ME" SHALL NOT be findable in the saved document
- **AND** the saved document SHALL NOT highlight any region for it

#### Scenario: Deleted text is absent from the serialised layer
- **WHEN** a slice is deleted
- **THEN** the layer serialised for the page SHALL NOT contain the deleted text
- **AND** SHALL still contain the text of the remaining slices

#### Scenario: Deleting a slice in the annotation layer
- **WHEN** an annotation note is deleted
- **THEN** the note SHALL be absent from the page's annotation layer
- **AND** SHALL not be drawn on the page

#### Scenario: The last slice of a line is deleted
- **WHEN** the only slice of a line is deleted
- **THEN** the line SHALL NOT be serialised as an empty element
- **AND** the serialised layer SHALL NOT contain an empty line

### Requirement: Emptying a slice deletes it

Accepting an empty text SHALL delete the slice, and the editor SHALL then show a
different slice rather than restoring the deleted text.

#### Scenario: Select all and delete the contents
- **WHEN** the user selects the whole text of a slice, deletes it, and accepts
- **THEN** the slice SHALL be deleted from the page's layer
- **AND** the control SHALL show the text of another slice, not the deleted text

#### Scenario: Deleting every slice on the page
- **WHEN** the user deletes the final remaining slice on a page
- **THEN** the editor SHALL be left with no slice focused
- **AND** the page's layer SHALL contain no text slices

### Requirement: Navigation continues from the affected slice

After a correction or a deletion, the editor SHALL leave the next surviving
slice focused, or the previous one if there is no next.

#### Scenario: Navigation advances past a deleted slice
- **WHEN** the user deletes a slice that has a following slice
- **THEN** the following slice SHALL become focused
- **AND** the deleted slice SHALL NOT be reachable by subsequent navigation

#### Scenario: Navigation falls back when the last slice is deleted
- **WHEN** the user deletes the final slice in navigation order
- **THEN** the preceding slice SHALL become focused

#### Scenario: A correction advances to the next surviving slice
- **WHEN** the user corrects a slice that has a following slice and accepts
- **THEN** the following slice in the current navigation order SHALL become
  focused
- **AND** the corrected slice SHALL remain present in the page's layer with its
  corrected text

#### Scenario: A correction advances past a slice in confidence order
- **WHEN** the user corrects a low-confidence slice while the editor is sorted
  by confidence
- **THEN** the next-least-confident surviving slice SHALL become focused

#### Scenario: A correction advances in reading order
- **WHEN** the user corrects a slice while the editor is sorted by position
- **THEN** the next slice in reading order SHALL become focused

#### Scenario: A correction on the final slice stays on that slice
- **WHEN** the user corrects the final slice in navigation order and accepts
- **THEN** the corrected slice SHALL remain focused

#### Scenario: Sorting order does not change what is edited
- **WHEN** the user switches the sort order between confidence and position
- **THEN** the slice shown in the control SHALL remain the same slice
- **AND** the text of that slice SHALL remain as displayed

### Requirement: The initial sort selection is applied to navigation

When the text layer editor first appears, the sort method shown selected in
the control SHALL be the method used by navigation, so the displayed selection
and the actual navigation order agree from the start without any user action.

#### Scenario: First entry navigates by the displayed method

- **WHEN** the user enters the text layer editor for the first time with the
  sort control showing "Sort by confidence"
- **THEN** activating the "go to least confident text" control SHALL move to
  the least confident slice, as if the confidence sort had been selected
- **AND** the user SHALL NOT need to change and change back the sort selection
  to get confidence-based navigation

#### Scenario: The displayed selection always matches navigation

- **WHEN** the sort control is set to either method
- **THEN** the navigation order SHALL follow that method without the user
  having to toggle the selection

### Requirement: The editor never offers a slice that no longer exists

The editor SHALL NOT leave a deleted slice focused, and SHALL NOT allow an edit
to be committed against it.

#### Scenario: Committing after a deletion acts on the surviving slice
- **WHEN** a slice is deleted and the user immediately types and accepts
- **THEN** the edit SHALL be applied to the slice the editor moved to
- **AND** the deleted slice SHALL remain absent from the page's layer

### Requirement: Slices can be added and duplicated

Adding a slice SHALL insert a new slice at the current selection, and
duplicating SHALL insert a copy of the current text at the current selection.
Both SHALL be written to the page's layer and drawn on the page.
#### Scenario: Adding a slice at the selection

- **WHEN** the user drags a selection, types a text and activates the add
control
- **THEN** a slice with that text SHALL exist at the selected rectangle
- **AND** it SHALL be drawn on the page
- **AND** the new slice SHALL be focused for further editing

#### Scenario: Adding a slice from a layer-pane selection

- **WHEN** the user draws a rectangle in the Text layer pane, types a text
  and activates the add control
- **THEN** a slice with that text SHALL exist at the drawn rectangle
- **AND** it SHALL be drawn on the page

#### Scenario: Adding uses a placeholder when no text is given
- **WHEN** the user activates the add control with an empty control and a
  selection
- **THEN** a slice SHALL be added at the selection with placeholder text
#### Scenario: Duplicating a slice

- **WHEN** the user activates the duplicate control
- **THEN** a second slice with the same text SHALL exist at the current
selection
- **AND** the original slice SHALL remain unchanged

### Requirement: The Add control is disabled without a selection

The Add control SHALL be disabled (ghosted) whenever there is no current
selection, and SHALL be enabled whenever there is one. This applies to both
the text and annotation editors.

#### Scenario: No selection disables the Add control

- **WHEN** there is no selection rectangle
- **THEN** the Add control SHALL be disabled
- **AND** activating it SHALL have no effect

#### Scenario: A selection enables the Add control

- **WHEN** a selection rectangle exists, whether drawn in the image view or a
  layer pane
- **THEN** the Add control SHALL be enabled

### Requirement: The disabled Add control explains itself

While the Add control is disabled it SHALL show a tooltip stating that a
rectangle must be drawn or selected before adding, so the reason for the
disabled state is discoverable.

#### Scenario: Tooltip on the disabled Add control

- **WHEN** the Add control is disabled
- **THEN** hovering it SHALL show a tooltip that a rectangle must be drawn or
  selected first

### Requirement: A first slice can be created on a page with no layer

If the page has no text layer, the first added slice SHALL establish the layer
for the page and SHALL be editable immediately.

#### Scenario: First slice on a page with no text layer
- **WHEN** the user activates the add control on a page with no text layer
- **THEN** the page SHALL gain a text layer containing that slice
- **AND** the slice SHALL be shown in the editing control

### Requirement: Cancel discards the pending edit

Activating the cancel control SHALL hide the editing control and SHALL NOT
commit the text currently in it.

#### Scenario: Cancelling an uncommitted correction
- **WHEN** the user edits the text in the control and activates cancel instead
  of accepting
- **THEN** the page's text layer SHALL retain the pre-edit text

### Requirement: Layer edits are undoable and redoable

Accepting a correction, adding, duplicating, or deleting a slice SHALL be
reversible with undo and re-applicable with redo, for both the text layer
and the annotation layer, including what is drawn on the page.

#### Scenario: Undo restores a deleted slice

- **WHEN** the user deletes a slice and triggers undo once
- **THEN** the slice SHALL be present in the page's layer again
- **AND** the slice SHALL be drawn on the page again

#### Scenario: Undo reverts a correction

- **WHEN** the user corrects a slice's text and triggers undo once
- **THEN** the slice's text in the layer SHALL be the text it had before
  the correction

#### Scenario: Redo re-applies the edit

- **WHEN** a layer edit is undone and the user triggers redo once
- **THEN** the layer SHALL contain the edited state again

#### Scenario: Annotation edits undo too

- **WHEN** an annotation note is deleted and the user triggers undo once
- **THEN** the note SHALL be present in the annotation layer again

### Requirement: A rebuilt layer clears the focused slice

Whenever the page's layer is rebuilt from the session - after undo or
redo, or when another page is loaded - the editor SHALL drop any slice it
had focused, and SHALL NOT apply a subsequent accept or delete to a slice
that is not part of the rebuilt layer.

#### Scenario: Undo while a slice is focused

- **WHEN** a slice is focused and the user triggers undo, which rebuilds
  the page's layer
- **THEN** the editing control SHALL NOT show the text of a slice that is
  absent from the rebuilt layer
- **AND** a following accept or delete SHALL act only on slices present in
  the rebuilt layer

#### Scenario: Loading another page drops the previous page's slice

- **WHEN** the user focuses a slice and then displays another page
- **THEN** the editing control SHALL NOT keep the previous page's slice
  focused

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

### Requirement: A new slice's orientation is guessed from its selection

When a slice is added, duplicated, or first created without an inherited
quarter-turn rotation, the editor SHALL choose the slice's text angle as the
orientation that draws its text largest in the selected rectangle. The angle
SHALL be 0 degrees when upright fits at least as well as rotated, and 90
degrees when the rotated fit is larger. An inherited quarter-turn rotation
from the focused slice or an ancestor SHALL be used instead of guessing.

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

### Requirement: A guessed text angle is an ordinary angle

A guessed angle SHALL be an ordinary text angle: it SHALL be drawn, persisted
in the page's layer, serialised in saved output, and remain correctable with
the rotate controls.

#### Scenario: A guessed rotation is correctable

- **WHEN** a slice created with a guessed rotation is focused and the user
  activates a rotate control
- **THEN** the slice's text angle SHALL change by that quarter turn
- **AND** the change SHALL be persisted in the page's text layer

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

### Requirement: The rotation controls act on the focused slice only

Rotating SHALL affect only the slice currently focused in the editor and SHALL
NOT change the rotation of any other slice.

#### Scenario: Rotating one slice leaves the others unchanged
- **WHEN** the user focuses one slice among several and rotates it
- **THEN** the other slices' text SHALL be drawn at their original angles
- **AND** the page's text layer SHALL keep the other slices' rotations
  unchanged
