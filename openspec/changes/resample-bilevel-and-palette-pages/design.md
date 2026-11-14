# Design

## Context

PDF downsampling in `Page.write_image_for_pdf()` and the DjVu resolution
equalisation in `Page._equalize_resolution()` both call
`Image.Image.resize()`. Pillow forces nearest-neighbour resampling for
bilevel (`1`) and palette (`P`) images whatever filter is requested. The
Ubuntu builds of Pillow 12.1 (26.04) and 12.3 (26.10) return `NULL` without
setting an exception from that path, so Python raises
`SystemError: <method 'resize' of 'ImagingCore' objects> returned NULL
without setting an exception`.

The fault is a bad Ubuntu backport of upstream commit `aafa6c7`, shipped as
`CVE-2026-112402.patch`. That commit was written for Pillow 13, where
`ImagingTransform()` returns an `int` (`0` on success). In the 12.x trees it
returns the output image, a non-`NULL` pointer on success, so the backported
`if (ImagingTransform(...))` treats success as failure, deletes the result
and returns `NULL` with no Python exception set. Only the nearest-neighbour
branch calls `ImagingTransform()`, which is why every mode fails with
NEAREST while modes `1` and `P` fail with any filter: Pillow coerces those
modes to NEAREST.

The PyPI builds of 12.1 and 12.3 are the unpatched upstream releases, and
PyPI 13.0.0 matches the commit's `int` return contract, so none of them
fail. Pillow 10.2 on 24.04 is unaffected. This is why the PyPI and Ubuntu
builds of the same version number behave differently.

## Goals / Non-Goals

**Goals:**

- Finish the save on every supported Pillow build.
- Produce the same output on every series, independent of the local build.
- Keep bilevel pages bilevel, so codec selection and stream size do not
  change.

**Non-Goals:**

- Patching Pillow or requiring a different build.
- Changing the target-resolution arithmetic or codec selection.
- Preserving the palette of a palette page: resampling palette indices is
  not meaningful, so palette pages are resampled in their true colours.

## Decisions

### Convert before resampling

Bilevel pages become 8-bit grayscale, are resampled with a box filter, and
are thresholded back to one bit with the existing `_to_bilevel()` threshold.
Palette pages become RGB, or RGBA when they carry transparency, before
resampling.

The box filter avoids the ringing a bicubic or Lanczos kernel would
introduce before thresholding a bilevel page, and it is the filter the DjVu
equalisation already uses.

Alternatives considered:

- **Detect the failing build and fall back.** Catching `SystemError` makes
  the output depend on the local Pillow build, and every series would still
  need its own test expectation. Rejected.
- **Resize the index plane in Python.** A pure-Python nearest-neighbour
  sampler keeps the old pixels but is far too slow for a full-page scan.
  Rejected.
- **Require a fixed Pillow version.** The failure is in the distribution's
  package, and users of the PPA cannot choose another. Rejected.

### Share the helper with DjVu

`_equalize_resolution()` resizes a page whose horizontal and vertical
resolutions differ. It calls the same helper, so a bilevel page saved as
DjVu does not hit the same crash. Returning a one-bit image keeps
`write_image_for_djvu()` choosing the `cjb2` encoder, exactly as before.

### Remove the workaround at end of life

Only the Ubuntu builds of Pillow 12.1 (26.04) and 12.3 (26.10) fail this
way. Once both series are out of support, `_resize_image()` can be replaced
by a plain `Image.Image.resize()` again, and the palette regression test,
which pins the converted RGB/RGBA mode, can be dropped. The same applies
earlier if Ubuntu corrects the backport in a package update. The helper's
docstring names the versions, the cause and the removal condition so the
workaround is not kept beyond its cause.
