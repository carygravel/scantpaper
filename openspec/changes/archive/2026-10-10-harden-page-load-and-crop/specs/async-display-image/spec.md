## ADDED Requirements

### Requirement: Reconcile phantom pages on load failure
When a full-resolution page load fails because the page is no longer present
in the document's current state, the viewer SHALL reconcile the frontend page
list instead of leaving the stale page in place. After reconciliation the page
SHALL be removed (or the list refreshed from the current document snapshot) so
it is not repeatedly reported as missing, and the view SHALL not display a
broken or partial page.

#### Scenario: Missing page is dropped from the list
- **WHEN** the viewer attempts to display a page that the document no longer
  contains
- **THEN** the stale page SHALL be removed from the page list
- **AND** the remaining pages SHALL be renumbered consistently

#### Scenario: Missing page error is not repeatedly logged
- **WHEN** a page that is no longer in the document is selected or displayed
- **THEN** after reconciliation the same page SHALL NOT be reported as missing
  again on subsequent display attempts

#### Scenario: Valid pages are unaffected
- **WHEN** a page load fails for a stale page while other pages remain valid
- **THEN** the valid pages SHALL continue to load and display normally
