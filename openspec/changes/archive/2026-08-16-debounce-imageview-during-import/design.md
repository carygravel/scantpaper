## Context

`_display_image(pageid)` (`session_mixins.py:237`) is called once per imported
page via the selection-changed handler (`app_window.py:697`). It shows the
thumbnail synchronously (`:247-249`), then sends a `get_page` request whose
`on_page_loaded` callback synchronously decodes the full-resolution page
(`page.py:321-325`) plus rebuilds text/annotation canvases.

Bulk import is **worker-bound**: each page requires `tiffcp` + DB insert +
thumbnail generation on the worker thread (`importthread.py`), so pages arrive
at the main loop one at a time, spaced over the whole import (minutes) — not in
a tight burst. Because the main loop idles between pages for longer than any
feasible debounce window, a time-based debounce fires between every page and the
viewer still sends+decodes `get_page` for each one. Scanning, by contrast, keeps
up comfortably page-by-page and must be left unchanged.

`SessionMixins`, `FileMenuMixins`, etc. are mixed into `ApplicationWindow`
(`app_window.py:102`), so they share `self`.

## Goals / Non-Goals

**Goals:**
- During a bulk import, do not load the full-resolution page for intermediate
  pages; show only the cheap thumbnail.
- After the import finishes, load the full-resolution image once for the last
  page.
- Leave scanning behaviour unchanged (still loads each scanned page full-res).

**Non-Goals:**
- Changing the worker response drain (`basethread.py`) or the DB schema.
- Optimizing `Page.get_pixbuf()` itself.
- Changing the selection-signal flow in `add_page`.

## Decisions

### D1: Suppress full-resolution loads during bulk import via a flag
Add a `_suppress_full_display` attribute on the window, defaulting to falsy.
- `_import_files` (`file_menu_mixins.py:243`) sets `self._suppress_full_display =
  True` before starting the import.
- `_import_files_finished_callback` (`file_menu_mixins.py:231`) clears it to
  `False` when the import completes, then triggers a single `_display_image` for
  the currently selected (last) page so the final page is shown full-res.
- In `_display_image` (`session_mixins.py:237`): always show the thumbnail
  synchronously; only send the `get_page` request when
  `self._suppress_full_display` is falsy.

Rationale: this prevents the request flood at the source during the import,
while keeping single-page and scanning behaviour identical. The thumbnail keeps
up during import (cheap, synchronous), and the full-res image appears once at
the end.

Alternatives considered: a `GLib.idle_add`/`timeout_add` debounce was tried but
fails because the import is worker-bound (pages spaced longer than the window),
so the timer fires between every page and every page is still loaded. A
stale-response guard was rejected because it still sends and decodes every
request.

### D2: Thumbnail-first UX preserved
The immediate `set_pixbuf(thumbnail, True)` stays in `_display_image`, so the
view updates instantly for every page during the import. Full-res only loads for
the final page.

### D3: Scanning and manual navigation unchanged
Scanning (`import_scan`, `document.py:278`) never sets the flag, so each
scanned page is loaded full-res exactly as before. Manual single-page navigation
is likewise unaffected.

## Risks / Trade-offs

- **Intermediate pages show only thumbnails during a bulk import**: acceptable,
  since the user sees every page's thumbnail and the final page at full res once
  the import completes. This is the intended behaviour for very large imports.
- **Flag lifetime**: the flag is cleared in the import `finished_callback`.
  Must be set and cleared in the same `_import_files` path; a flag left set by a
  failed import would suppress future loads, so ensure the finished callback
  always runs.
- **Tests**: tests for `_import_files`/`_display_image` must set or clear the
  flag as appropriate; existing `_display_image` tests (which do not set the
  flag) continue to expect an immediate `get_page`.
