## ADDED Requirements

### Requirement: Session open resumes full-resolution display
When a saved session is opened through the File → Open import flow, the viewer
SHALL display the selected page at full resolution and render its text and
annotation layers once the session has finished loading. The thumbnail-only
display used during bulk imports SHALL NOT persist after a session is opened.

#### Scenario: Full-resolution image after opening a saved session
- **WHEN** a saved session file is opened via File → Open
- **THEN** after the session finishes loading, the selected page SHALL be
  displayed at full resolution
- **AND** the page's text layer SHALL be rendered

#### Scenario: Page switching stays full resolution after a session open
- **WHEN** a session was opened via File → Open
- **AND** the user selects another page
- **THEN** that page SHALL be loaded and displayed at full resolution
- **AND** its text layer SHALL be rendered