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

#### Scenario: Sorting order does not change what is edited
- **WHEN** the user switches the sort order between confidence and position
- **THEN** the slice shown in the control SHALL remain the same slice
- **AND** the text of that slice SHALL remain as displayed

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
