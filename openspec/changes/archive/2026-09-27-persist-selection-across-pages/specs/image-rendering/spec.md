## ADDED Requirements

### Requirement: Selection clamping uses the full-resolution image
When re-applying a selection during a page change, the image view SHALL clamp
the selection against the page's full-resolution image dimensions rather than
the transient thumbnail pixbuf currently being displayed. Clamping a selection
against a reduced-size thumbnail that produces a zero or negative width or
height SHALL NOT occur, so a valid selection always remains drawable.

#### Scenario: Full-resolution selection not clamped to thumbnail size
- **WHEN** a selection is made on a full-resolution page and the page is
  switched, with a thumbnail displayed during the transition
- **THEN** the selection SHALL be clamped to the full-resolution image
  dimensions, not degraded to a zero/negative size by the thumbnail
