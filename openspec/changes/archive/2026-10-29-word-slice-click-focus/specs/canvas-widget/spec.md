# Spec Delta

## ADDED Requirements

### Requirement: A primary press focuses only a word slice

A primary-button press on the Canvas SHALL focus a slice only when the pointer
lands on a word box. A press that lands on any other box, or on no box, SHALL
NOT focus anything, SHALL NOT change the active navigation order or its
current position, and SHALL begin a selection drag when the page extent is
known. The geometric lookup that resolves a box at a point SHALL remain
available for choosing a new slice's parent.

#### Scenario: A press on a word focuses that word

- **WHEN** a word box is displayed under the pointer
- **AND** the user presses the primary button
- **THEN** that word SHALL become the focused slice
- **AND** no selection drag SHALL begin

#### Scenario: A press in the whitespace of a container starts a selection

- **WHEN** a line, paragraph, column or page box covers the pointer position
- **AND** no word box covers that position
- **AND** the page extent is known
- **AND** the user presses and drags the primary button
- **THEN** a rubber-band rectangle SHALL follow the pointer
- **AND** on release the rectangle SHALL become the current selection

#### Scenario: A press in container whitespace does not disturb navigation

- **WHEN** the editor is sorted by confidence and a word is focused
- **AND** the user presses the primary button in the whitespace of a container
- **THEN** no error SHALL be raised
- **AND** the focused slice SHALL remain the slice that was focused
- **AND** subsequent next and previous navigation SHALL continue from it

#### Scenario: Parent lookup still resolves a container

- **WHEN** a new slice is added at a selection whose centre lies in the
  whitespace of a container
- **THEN** the container SHALL be usable as the new slice's parent
- **AND** this SHALL NOT make the container a focusable slice
