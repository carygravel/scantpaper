## ADDED Requirements

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