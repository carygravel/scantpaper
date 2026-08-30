# page-reordering

## Purpose

Governs how pages are reordered by drag-and-drop in the page list: reordering
dispatches through a dedicated operation on the worker thread that moves pages
in place, is a single undoable action, and does not duplicate stored image data.

## Requirements

### Requirement: Drag-and-drop reorder dispatches a dedicated operation
Dragging a page (or selection of pages) to a new position SHALL dispatch a
single dedicated reorder operation to the worker thread, rather than cloning the
pages and deleting the originals.

#### Scenario: Reordering a single page
- **WHEN** the user drags one page from the top of the list to a position near the bottom
- **THEN** exactly one reorder operation SHALL be dispatched to the worker thread
- **AND** the page SHALL appear at the new position after the operation completes

#### Scenario: Reordering a multi-page selection
- **WHEN** the user drags a selection of several pages to a new position
- **THEN** the selected pages SHALL be moved as a block to the new position in a single reorder operation
- **AND** the relative order of the selected pages SHALL be preserved

### Requirement: Reorder preserves stored image data
Reordering pages SHALL NOT copy or re-encode any stored image data. Each
reordered page SHALL keep its existing stored image reference.

#### Scenario: Image blobs are not duplicated on reorder
- **WHEN** a page is dragged to a new position
- **THEN** no new image rows SHALL be inserted into storage for that page
- **AND** the page SHALL retain its original stored image reference

### Requirement: Reorder is a single undoable action
A drag-and-drop reorder SHALL be recorded as a single undo step, so that undo
restores the document to the state before the drag in one operation.

#### Scenario: Undo after a reorder restores original order
- **WHEN** a page is reordered by drag-and-drop and the user triggers undo once
- **THEN** the document SHALL return to the page order it had before the drag
- **AND** the reorder SHALL NOT require more than one undo to revert

### Requirement: Reorder keeps page numbers consecutive
After a reorder, page numbers SHALL be re-derived from positions so they remain
exactly 1..n with no gaps and no duplicates.

#### Scenario: Dragging to the bottom renumbers consecutively
- **WHEN** the first page of an n-page document is dragged to the bottom
- **THEN** the dragged page SHALL become number n and all pages SHALL be numbered 1..n consecutively in the new order

### Requirement: Reorder preserves selection semantics
Reordering SHALL NOT corrupt the current selection. The moved pages SHALL
remain selected after the reorder completes, subject to the normal post-drop
selection behaviour.

#### Scenario: Moved pages remain selected
- **WHEN** a selection of pages is dragged to a new position
- **THEN** the moved pages SHALL still be selected after the operation completes