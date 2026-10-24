# list-typeahead Specification

## Purpose
Governs whether the application's list widgets engage GtkTreeView interactive
(typeahead) search, so that typing in a focused list never pops up a dead
search overlay and never triggers the upstream GTK CSS-node assertion.

## Requirements

### Requirement: List widgets do not initiate typeahead search

The application's list widgets SHALL NOT start GtkTreeView interactive
(typeahead) search when the user presses a printable key while the list has
keyboard focus. Typing in a focused list SHALL NOT open the interactive-search
overlay and SHALL NOT emit the upstream GTK `gtk_css_node_insert_after`
critical message.

#### Scenario: Typing in the thumbnail list

- **WHEN** the user presses a printable character while the thumbnail list
  has keyboard focus
- **THEN** no interactive-search overlay SHALL appear
- **AND** no `gtk_css_node_insert_after` critical message SHALL be emitted

#### Scenario: Typing in the crashed-session picker

- **WHEN** the user presses a printable character while the crashed-session
  picker list has keyboard focus
- **THEN** no interactive-search overlay SHALL appear
- **AND** no `gtk_css_node_insert_after` critical message SHALL be emitted

#### Scenario: Every list widget is covered

- **WHEN** the application constructs any list widget (including the
  document's thumbnail list and any picker list)
- **THEN** that widget's typeahead search SHALL be disabled, so that pressing
  a printable key cannot open the interactive-search overlay or emit the
  critical message
