## Why

The text-layer and annotation canvases no longer line up with the image
view. Investigation (live, after real OCR) verified: in tabbed mode the
canvases are hidden `GtkStack` pages whose allocation is `0x0` (never
shown) or stale (shown before, then hidden). The canvas clamps every
incoming offset against `get_allocation()` (canvas.py:584), so the
view's fitted offset — pushed both by the bidirectional bindings and
explicitly by the layer editor (`LayerEditor.set_extent`/`create`) — is
destroyed while the canvas is hidden: `set_offset(357, 0)` on an
unmapped canvas leaves `(0, 0)`. Verified push on an allocated canvas
centres correctly, and nothing re-syncs on (re)allocation: after OCR
plus a tab switch the view sat at `off=(357,0)` while the canvas stayed
`off=(0,0)`.

The visible result: text/annotation content hugs the top-left corner
while the image tab shows the page centred; after a window shrink the
stale clamp can put the page entirely off-screen so the tab looks
empty. The same defects were dormant until the image view started
re-fitting on allocation (fix-imageview-display), which now pushes new
offsets to canvases that cannot absorb them.

## What Changes

- The canvas SHALL defer offset clamping while its allocation is not
  usable (unmapped or `0x0`), storing the pushed offset unchanged, and
  SHALL re-clamp and re-emit on allocation — the defer-and-recover
  pattern already applied to the image view.
- The canvas SHALL re-clamp its offset whenever it is allocated, so a
  canvas shown after being hidden aligns with the view at the moment it
  becomes visible.
- Regression tests covering: offset pushed while unmapped is preserved
  and clamped correctly at first allocation; canvas aligns with the
  view after a tab switch; window shrink followed by tab switch does
  not leave the page off-screen.

## Capabilities

### New Capabilities
- `canvas-view-sync`: The text-layer and annotation canvases track the
  image view's zoom and offset across allocation changes and hidden
  periods, so switching tabs shows the same region of the page as the
  image view.

### Modified Capabilities
- `canvas-widget`: The offset-clamping requirement is made precise:
  clamping SHALL happen against a live allocation, never a stale or
  zero one; an offset pushed while unallocated SHALL be preserved and
  clamped at the next allocation.

## Impact

- Code: `src/scantpaper/canvas.py` (offset setter, new
  `do_size_allocate` override), tests.
- Possibly a symmetric guard in `src/scantpaper/imageview.py`'s offset
  setter for pushes received while the view is a hidden stack page.
- No dependency, data-model, or file-format changes.
- Repairs user-visible behaviour broken during the GTK4 migration and
  exposed by the image-view re-fit fix.
