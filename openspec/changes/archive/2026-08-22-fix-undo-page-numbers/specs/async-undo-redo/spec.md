## ADDED Requirements

### Requirement: Undo and redo restore 1-based page numbering
The snapshots delivered by undo and redo SHALL carry page numbers that are
1-based positions in the restored order, identical to what the page list would
display for that order. Snapshot page numbers SHALL NOT expose internal
storage row identifiers or zero-based indices.

#### Scenario: Undoing a deletion restores consecutive numbering
- **WHEN** the first page of a three-page document is deleted and the
  deletion is undone
- **THEN** the restored pages SHALL be numbered 1, 2, 3

#### Scenario: Redo of a deletion keeps numbering consecutive
- **WHEN** a deletion is undone and then reapplied with redo
- **THEN** the remaining pages SHALL be numbered consecutively from 1

#### Scenario: Restored numbers always match positions
- **WHEN** any document state is restored via undo or redo
- **THEN** each restored page number SHALL equal its 1-based position in the
  restored order, with no gaps and no duplicates
