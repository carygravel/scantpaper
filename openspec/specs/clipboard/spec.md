# clipboard

## Purpose

Provides a window-scoped copy/cut/paste clipboard for scanned pages, storing
the copied or cut page data separately from any one document and signalling
when its contents change so the UI can react.

## Requirements

### Requirement: Clipboard stores copied or cut page data
The application SHALL maintain a single clipboard per main window that stores
the page data produced by a copy or cut operation, and SHALL expose whether it
currently holds data.

#### Scenario: Copy stores page data
- **WHEN** the user copies a selection
- **THEN** the clipboard SHALL hold the copied page data and SHALL report that
  it has data

#### Scenario: Cut stores page data
- **WHEN** the user cuts a selection
- **THEN** the clipboard SHALL hold the cut page data and SHALL report that it
  has data

#### Scenario: Empty copy leaves clipboard empty
- **WHEN** the user copies with no pages selected
- **THEN** the clipboard SHALL hold no data and SHALL report that it is empty

#### Scenario: Empty cut clears prior contents
- **WHEN** the user cuts with no pages selected after a previous copy or cut
- **THEN** the clipboard SHALL be cleared (hold no data), even if it previously
  held data

### Requirement: Clipboard signals when its contents change
The clipboard SHALL notify listeners whenever its contents change (become
non-empty, become empty, or are replaced), so the UI can update without being
explicitly told to refresh.

#### Scenario: Listeners notified on change
- **WHEN** the clipboard contents change
- **THEN** the clipboard SHALL emit a change notification to its listeners

#### Scenario: Paste action reflects clipboard state
- **WHEN** the clipboard changes
- **THEN** the paste action SHALL be enabled if the clipboard has data and
  disabled if it is empty

### Requirement: Clipboard persists across document replacement
The clipboard SHALL belong to the main window rather than to any single
document, so it remains populated when the underlying document is replaced
(e.g. starting a new session).

#### Scenario: Clipboard survives a new document
- **WHEN** the document is replaced but the window is unchanged
- **THEN** the clipboard SHALL retain its page data and the paste action SHALL
  remain enabled

### Requirement: Paste uses the stored clipboard data
Pasting SHALL insert the pages currently held by the clipboard into the
document, either after the last selected page or, when nothing is selected, at
the end of the document.

#### Scenario: Paste after a selection
- **WHEN** the user pastes with pages selected
- **THEN** the clipboard's page data SHALL be inserted after the last selected
  page and the new pages SHALL be selected

#### Scenario: Paste with nothing selected
- **WHEN** the user pastes with no pages selected
- **THEN** the clipboard's page data SHALL be inserted at the end of the
  document

#### Scenario: Paste with empty clipboard does nothing
- **WHEN** the user pastes and the clipboard is empty
- **THEN** no pages SHALL be inserted

### Requirement: Clipboard is sticky after paste
Pasting SHALL NOT clear the clipboard; the stored page data SHALL remain
available until the next copy or cut replaces it.

#### Scenario: Clipboard retained after paste
- **WHEN** the user pastes and then pastes again without copying or cutting
- **THEN** the second paste SHALL insert the same page data again
