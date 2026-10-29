# Spec Delta

## ADDED Requirements

### Requirement: The editor focuses only word slices

The layer editor SHALL focus, display, rotate, edit or delete only word slices.
A page, column, paragraph or line box SHALL never become the focused slice, so
neither accepting an unchanged control nor correcting it can rewrite or remove
a container. A press that does not land on a word SHALL leave the previously
focused slice focused.

#### Scenario: A press in container whitespace keeps the previous slice

- **WHEN** a word slice is focused in the editor
- **AND** the user presses the primary button on whitespace inside a container
- **THEN** the control SHALL keep showing the focused slice's text
- **AND** the previously focused slice SHALL remain focused

#### Scenario: Confidence order is not disturbed by a container press

- **WHEN** the editor is sorted by confidence
- **AND** the user presses the primary button on whitespace inside a container
- **THEN** no error SHALL be raised
- **AND** the control SHALL still show the previously focused slice

#### Scenario: Accepting after a container press does not delete a container

- **WHEN** the editor is sorted by position
- **AND** the user presses the primary button on whitespace inside a line
- **AND** the user then accepts the control without typing
- **THEN** the line and its words SHALL remain in the page's layer
- **AND** the previously focused slice SHALL remain in the page's layer

#### Scenario: Annotations follow the same rule

- **WHEN** the annotation editor is active
- **AND** the user presses the primary button on whitespace inside a container
- **THEN** the container SHALL NOT become the focused annotation
- **AND** the previously focused annotation SHALL remain focused
