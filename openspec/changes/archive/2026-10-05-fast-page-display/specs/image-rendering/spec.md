## MODIFIED Requirements

### Requirement: Efficient pixbuf creation for page display

The system SHALL create page display pixbufs efficiently without writing full-resolution images to temporary PNG files, reducing page switching latency for large color scans.

#### Scenario: Large color scan page switch performance
- **WHEN** switching to a page containing a large color scan (e.g., 600 dpi A4)
- **THEN** the display pixbuf is created quickly without full-resolution PNG encode/decode roundtrips
- **AND** the rendered image is identical in appearance to the previous behavior

#### Scenario: Pixbuf creation error handling preserved
- **WHEN** pixbuf creation fails due to an error condition
- **THEN** the method returns `None` as before
- **AND** error handling remains compatible with existing tests and code paths

#### Scenario: All image modes supported
- **WHEN** creating pixbufs from images in any supported PIL mode (RGB, RGBA, LA, PA, P, 1, L, I, and 16-bit variants)
- **THEN** correct pixbufs are created with proper color channels and alpha handling
