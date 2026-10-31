# Proposal

## Why

The GTK4 migration replaced GTK3's window-grab helper with rendering widgets
into Cairo `ImageSurface` objects and reading raw `ARGB32` pixels. Two test
helpers decode that memory as if every host were little-endian. Cairo stores
`ARGB32` values native-endian, so on s390x the same correct pixel decodes as a
different colour. Four tests fail on s390x even though the application renders
the right output:

- `test_transparency`
- `test_filter`
- `test_imageview_selection_is_themeable`
- `test_canvas_selection_is_themeable`

The immediate effect is that the Debian testing migration is blocked. The
deeper problem is visibility: every little-endian release architecture passes,
so a hard-coded byte order can survive indefinitely and only surface when a
big-endian build runs. The test suite should make the assumption explicit and
exercise both layouts on the architectures CI already has.

## What Changes

- Introduce one byte-order-aware `ARGB32` decoder for the test suite, using the
  host byte order by default.
- Use it in the image-view offscreen reader instead of unpacking the first
  three bytes as blue, green and red.
- Use it in the canvas pixel reader instead of comparing raw bytes with a
  little-endian literal.
- Add a regression test that decodes explicit little-endian and big-endian byte
  sequences to the same colours, so a future reintroduction fails on any
  existing runner.
- Document in the helper that Cairo's `ARGB32` layout is native-endian.

No production code, user-visible behaviour, dependency or packaging change is
involved.

## Capabilities

### New Capabilities

None. This is test infrastructure only; it does not change a system behaviour.
The change records a deliberate spec opt-out with `skip_specs: true`.

### Modified Capabilities

None.

## Impact

- `src/scantpaper/tests/test_imageview.py`: the offscreen surface reader and
  the tests that compare absolute colours.
- `src/scantpaper/tests/test_7_canvas.py`: the canvas pixel helper and
  `test_canvas_selection_is_themeable`.
- Test helper code under `src/scantpaper/tests/` and its unit test.
- No runtime, API, dependency or packaging impact.
- Enables the four s390x autopkgtest failures to pass once a release includes
  the change. No new CI architecture is required, because the regression test
  exercises both byte orders on the existing runners.
