## Purpose

## MODIFIED Requirements

### Requirement: Thumbnail-first display
`_display_image(pageid)` SHALL show the thumbnail pixbuf from `self.data[i][1]`
immediately (synchronous), then send `"get_page"` asynchronously to load the
full-resolution image. During a bulk import of many pages, intermediate pages
SHALL show only the thumbnail; a full-resolution load SHALL be deferred until
the import completes.

#### Scenario: Immediate thumbnail display
- **WHEN** `_display_image(pageid)` is called
- **THEN** the thumbnail pixbuf from `self.data` SHALL be set on the view
  immediately, without waiting for the async response

#### Scenario: Full-res replaces thumbnail
- **WHEN** the async `"get_page"` response arrives
- **THEN** the full-resolution pixbuf SHALL replace the thumbnail on the view
- **AND** the resolution ratio SHALL be updated
- **AND** the crop dialog dimensions SHALL be updated
- **AND** the text canvas SHALL be created or cleared based on the page's text layer
- **AND** the annotation canvas SHALL be created or cleared based on annotations

#### Scenario: Bulk import defers full-resolution load
- **WHEN** a bulk import is in progress and `_display_image` is called for an
  intermediate page
- **THEN** the thumbnail SHALL be shown
- **AND** no `"get_page"` request SHALL be sent for the intermediate page

#### Scenario: Import completion loads the final page full-res
- **WHEN** a bulk import finishes
- **THEN** a full-resolution load SHALL be requested for the current (last) page
- **AND** subsequent `_display_image` calls SHALL resume sending `"get_page"`
