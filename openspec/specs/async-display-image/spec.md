# async-display-image

Purpose: Async image display with thumbnail-first UX for the document viewer.

## Requirements

### Requirement: Async get_page dispatch
`DocThread` SHALL handle get_page requests via the `send("get_page", ...)` mechanism.
The `do_get_page()` handler SHALL execute on the worker thread, performing the full
SQLite query, image deserialization, and `Page.from_bytes()` construction.

#### Scenario: Page returned via async response
- **WHEN** `send("get_page", id=page_id, finished_callback=cb)` is called
- **THEN** the worker thread SHALL fetch the image blob and metadata from SQLite
- **AND** construct a `Page` object via `Page.from_bytes()`
- **AND** invoke `finished_callback` with the `Page` object as `response.info`

#### Scenario: Page not found
- **WHEN** `send("get_page", id=invalid_id, error_callback=err_cb)` is called
- **AND** no page matches the given id
- **THEN** `error_callback` SHALL be invoked with a `ValueError`

### Requirement: Thumbnail-first display
`_display_image(pageid)` SHALL show the thumbnail pixbuf from `self.data[i][1]`
immediately (synchronous), then send `"get_page"` asynchronously to load the
full-resolution image.

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

### Requirement: Deferred secondary UI updates
Crop dialog dimensions, text canvas, and annotation canvas SHALL NOT be updated
until the full-resolution page is loaded. They SHALL remain in their previous
state during the thumbnail-to-fullres transition.

#### Scenario: Crop dialog shows previous page state during load
- **WHEN** `_display_image(pageid)` is called
- **AND** the full-resolution page has not yet loaded
- **THEN** the crop dialog SHALL retain the previous page's dimensions
- **AND** text and annotation canvases SHALL retain their previous state

### Requirement: get_page_sync test helper
A `get_page_sync(thread, **kwargs)` helper SHALL be available for tests. It SHALL
send `"get_page"` and block on a nested `GLib.MainLoop` until the callback fires,
returning the `Page` object.

#### Scenario: Test helper returns page synchronously
- **WHEN** `get_page_sync(thread, id=page_id)` is called in a test
- **THEN** it SHALL block until the async response arrives
- **AND** return the `Page` object
