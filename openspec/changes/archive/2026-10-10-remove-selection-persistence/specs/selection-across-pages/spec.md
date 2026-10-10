## ADDED Requirements

### Requirement: Selection does not persist across application launches

The image selection rectangle SHALL be transient state that lives only for the
duration of the current session. It SHALL NOT be written to the user's config
file on exit, and SHALL NOT be restored on the next application launch, so a
stale selection from a previous session is never re-applied to a freshly opened
document.

#### Scenario: Selection is not written to the config file

- **WHEN** the user draws a selection rectangle and then quits the application
- **THEN** the selection is not stored in the user's config file

#### Scenario: No selection on a fresh launch

- **WHEN** the application is started after a previous session that had an
  active selection rectangle
- **THEN** no selection rectangle is present when a document is first displayed

#### Scenario: Within-session selection still works

- **WHEN** the user draws a selection and navigates between pages in the same
  session
- **THEN** the selection SHALL remain visible across page changes, per the
  existing page-navigation requirements
