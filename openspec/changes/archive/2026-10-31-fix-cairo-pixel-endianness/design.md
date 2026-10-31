# Design

## Context

See `proposal.md` - Why.

After the GTK4 migration, pixel assertions render a widget's draw function
into a Cairo `ImageSurface` and inspect `ImageSurface.get_data()`. Cairo
documents `CAIRO_FORMAT_ARGB32` as a 32-bit value with alpha in the upper 8
bits, then red, green and blue, stored **native-endian**. The two existing
readers assume the little-endian byte layout:

- `src/scantpaper/tests/test_imageview.py` - `_SurfaceReader.__init__` unpacks
  `raw[offset : offset + 3]` as blue, green, red.
- `src/scantpaper/tests/test_7_canvas.py` - `_canvas_pixel` returns raw bytes
  and `test_canvas_selection_is_themeable` compares them with a little-endian
  literal.

Production rendering never reads raw surface memory, so this is test-side only.

## Goals / Non-Goals

**Goals:**

- Decode Cairo `ARGB32` pixels correctly on every host byte order.
- Keep the byte-order assumption in one place, with a name that makes it
  visible.
- Exercise both byte orders in a regression test that runs on the existing
  little-endian CI runners.
- Keep `get_pixel()` and `_find_pixel()` working unchanged for callers.

**Non-Goals:**

- Changing any rendering, CSS, or selection behaviour.
- Adding alpha-aware assertions or handling premultiplied alpha differently from
  today. The readers stay RGB-only.
- Adding an s390x CI runner or changing Debian packaging.
- Optimising the existing per-pixel Python loops.

## Decisions

### 1. One pure decoder, parameterised by byte order

Add a test helper:

```text
src/scantpaper/tests/pixel_helpers.py

argb32_rgb(raw: bytes, offset: int, byteorder: str = sys.byteorder)
    -> tuple[int, int, int]
```

It reads four bytes as a native integer, then extracts red, green and blue:

```text
value = int.from_bytes(raw[offset : offset + 4], byteorder)
red   = (value >> 16) & 0xFF
green = (value >> 8)  & 0xFF
blue  =  value        & 0xFF
```

The `byteorder` parameter exists so the regression test can feed both layouts
explicitly. Callers use the default, `sys.byteorder`.

**Alternative considered:** duplicate the three-line decode in each test file.
Rejected: the duplication is exactly how the two independent assumptions arose,
and there would be no single place to regression-test.

**Alternative considered:** use `struct.unpack_from("=I", ...)`. Rejected:
`int.from_bytes` states the byte order explicitly and needs no struct
alignment reasoning.

### 2. Keep the pixel reader interfaces stable

`_SurfaceReader` continues to expose a three-channel RGB buffer through
`get_pixels()`, `get_rowstride()` and `get_n_channels()`, so `get_pixel()` and
`_find_pixel()` need no changes. Only the inner conversion changes:

```text
red, green, blue = argb32_rgb(raw, offset, sys.byteorder)
```

`_canvas_pixel` changes from returning four raw bytes to returning an
`(r, g, b)` tuple. Its comparisons and `_canvas_selection_center_pixel` follow,
and the themeable assertion becomes `overridden_pixel == (255, 0, 0)`.

```text
cairo.ImageSurface (ARGB32, native-endian)
              |
              v
       raw bytes + stride
              |
              v
  argb32_rgb(raw, offset, sys.byteorder)
              |
      +-------+--------+
      v                v
 _SurfaceReader    _canvas_pixel
      |                |
 get_pixel()       test assertions
 _find_pixel()
```

**Alternative considered:** convert the surface to `GdkPixbuf` and read that.
Rejected: GTK4 no longer offers the `Gdk.pixbuf_get_from_window` path that the
old tests used, and constructing a pixbuf from ARGB32 would still require a
byte-order-aware conversion.

### 3. Test both byte orders directly

Add a focused test, for example in `src/scantpaper/tests/test_pixel_helpers.py`,
parameterised with explicit byte sequences:

| byte order | raw bytes | expected RGB |
| --- | --- | --- |
| little | `00 00 FF FF` | `(255, 0, 0)` |
| big | `FF FF 00 00` | `(255, 0, 0)` |
| little | `00 FF 00 FF` | `(0, 255, 0)` |
| big | `FF 00 FF 00` | `(0, 255, 0)` |

Red catches the red/blue swap seen in the s390x log; green catches a green-byte
offset error. The test passes explicit byte orders, so it runs identically on
the existing little-endian runners and fails if someone hard-codes a layout
again.

## Risks / Trade-offs

- **The per-pixel Python loop stays slow** -> No complexity change; this is
  existing test behaviour and not part of the fix. The helper adds one function
  call per pixel, which the affected tests already tolerate.
- **Alpha and premultiplied colour are ignored** -> This matches the current
  reader. The failing and passing tests assert opaque or fully composited
  pixels. If a future test needs translucency, extending the helper is a
  separate change.
- **`sys.byteorder` is only correct while Cairo keeps its documented native-
  endian layout** -> The explicit two-order regression test guards the decoder;
  a real s390x run remains the end-to-end check.
- **Coverage gate** -> The new helper is a pure function with no branches, and
  its regression test covers every line; the 99% gate should be unaffected.

## Migration Plan

1. Land the helper, the two reader changes and the regression test together.
2. Run `pytest`, `ruff check`, `ruff format --check` and `ty check .`.
3. Ship the test-only change in the next release so the Debian autopkgtest on
   s390x picks it up.
4. Rollback is a plain revert; there is no runtime or data migration.
