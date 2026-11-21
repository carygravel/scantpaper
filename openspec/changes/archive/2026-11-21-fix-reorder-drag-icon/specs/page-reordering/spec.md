# Spec Delta

## ADDED Requirements

### Requirement: Reorder drag icon represents the dragged page

While a page reorder drag is in progress, the drag icon SHALL represent the
dragged page rather than the internal drag payload. The icon SHALL show the
thumbnail of a dragged page when one is available, and SHALL never display the
internal payload string.

#### Scenario: Dragging a page with a thumbnail

- **WHEN** the user starts dragging a selected page that has a thumbnail
- **THEN** the drag icon SHALL show that page's thumbnail
- **AND** the drag icon SHALL NOT show the internal payload text

#### Scenario: Dragging a multi-page selection

- **WHEN** the user starts dragging a selection of several pages
- **THEN** the drag icon SHALL show the thumbnail of one of the dragged pages
- **AND** the drag icon SHALL NOT show the internal payload text

#### Scenario: Dragging a page without a thumbnail

- **WHEN** the user starts dragging a selected page whose thumbnail is not
  available
- **THEN** the drag SHALL still begin
- **AND** the drag icon SHALL NOT show the internal payload text
