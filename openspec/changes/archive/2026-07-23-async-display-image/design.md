## Context

`_display_image()` (`session_mixins.py:243`) is called every time the user selects
a different page in the thumbnail list. It:

1. Calls `self.slist.thread.get_page(id=pageid)` — fetches full image blob from
   SQLite, deserializes via PIL, constructs a `Page` object. **This is the stall.**
2. Sets the pixbuf on the view
3. Updates resolution ratio
4. Updates crop dialog dimensions
5. Validates text layer (corrupt check)
6. Creates text and annotation canvases

The thumbnail pixbufs are already loaded in `self.data[i][1]` (from
`page_number_table()` during Phase 2). These are 100px thumbnails stored as PNG
blobs — small enough to deserialize in <1ms.

The method is called from:
- `app_window.py:700` — `_page_selection_changed_callback` (GTK signal handler)
- `session_mixins.py:241` — `_display_callback` (after async import/save operations)

The print operation (`print_operation.py:46`) also calls `thread.get_page()`
synchronously, but this is deferred to a follow-up change.

## Goals / Non-Goals

**Goals:**
- Show a thumbnail immediately on page selection (zero-latency feedback)
- Load full-resolution image asynchronously, replace thumbnail when ready
- Defer crop dialog, text canvas, and annotations until full-res loads
- Provide a test helper for the many test files that call `thread.get_page()`

**Non-Goals:**
- Print operation prefetch (follow-up change)
- LRU caching of deserialized pages
- Pre-fetching on hover

## Decisions

### D1: Thumbnail from self.data[i][1], not a separate fetch

**Choice:** Use the pixbuf already in `self.data[i][1]` for the immediate display.

**Alternative considered:** Fetch the thumbnail from the database separately.

**Rationale:** The thumbnail pixbufs are already in memory — they were loaded into
the TreeView model during `page_number_table()`. Using them directly avoids an
extra database round-trip and keeps the immediate display truly synchronous.

### D2: Split _display_image into sync + async phases

**Choice:** The sync phase sets the thumbnail on the view. The async phase
`send("get_page", ...)` with a callback that does all remaining work (full-res
pixbuf, crop dialog, text canvas, annotations).

**Alternative considered:** Keep `_display_image` synchronous by making `get_page`
synchronous (reverting the tiered decision).

**Rationale:** This is the core of the tiered model — `get_page()` involves image
deserialization and belongs in Tier 2 (async). The thumbnail-first approach gives
instant visual feedback while the full-res loads in the background.

### D3: Test helper uses nested GLib.MainLoop

**Choice:** Provide `get_page_sync(thread, **kwargs)` that sends `"get_page"` and
blocks on a nested `GLib.MainLoop` until the callback fires.

**Alternative considered:** Use threading.Event or asyncio.Future.

**Rationale:** The nested `GLib.MainLoop` pattern is already used in
`DocThread.__init__()` (`docthread.py:86-108`) and in test fixtures
(`conftest.py`). It integrates naturally with the GLib-based notification system
and doesn't require new synchronization primitives.

### D4: Crop dialog and canvases deferred to callback

**Choice:** Crop dialog dimensions, text canvas, and annotation canvas are only
updated in the `finished_callback`, not in the sync phase.

**Rationale:** These depend on the full `Page` object (text_layer, annotations,
full dimensions). Showing them with thumbnail data would be incorrect — the
thumbnail dimensions don't match the full image. Better to leave them in their
current state until the full-res loads.

## Risks / Trade-offs

- **[Thumbnail-to-fullres pop]** → User may see a brief visual transition from
  thumbnail to full-resolution. Mitigation: for most images this is <300ms. The
  thumbnail is a reasonable preview that gives context while loading.

- **[Crop dialog stale during load]** → Crop dialog shows old page dimensions until
  full-res loads. If user opens crop dialog during the load, they see stale data.
  Mitigation: this is a narrow window and the crop dialog is not commonly opened
  immediately after page selection.

- **[Test changes across ~15 files]** → Every test calling `thread.get_page()`
  needs to switch to the helper. Mitigation: the helper is a mechanical replacement.
  Could be done with a search-and-replace pattern.
