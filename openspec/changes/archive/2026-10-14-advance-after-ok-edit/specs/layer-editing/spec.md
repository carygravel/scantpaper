## MODIFIED Requirements

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
