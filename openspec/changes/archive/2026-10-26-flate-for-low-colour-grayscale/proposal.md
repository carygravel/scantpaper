# Proposal

## Why

Automatic compression picks JPEG for every continuous-tone page, including
8-bit grayscale. That is the right default for photographs, but it is exactly
wrong for the scans this application is built to produce: a page of black text
on white with a posterised (few-level) picture. JPEG's transform assumes smooth
tone, so the hard edges between a handful of intensity levels become
high-frequency energy it cannot compress, producing ringing and a stream
*larger* than a lossless one. Measured on the reported page, an 8-level
grayscale TIFF at 2721x4104: lossless Flate is 803 KB, JPEG at quality 50 is
1104 KB, and at quality 75 (the default) 1573 KB. The default "Automatic" thus
makes such a file roughly twice as large as it needs to be, and lossy as well.

The damage starts earlier: on import an 8-bit grayscale TIFF is stored as JPEG
quality 92, so one lossy generation is applied before the user chooses
anything, and the stored blob for the reported 624 KB TIFF grows to 2.5 MB.

## What Changes

- Recognise continuous-tone images with few distinct intensity levels
  (posterised scans) and treat them as lossless rather than as photographic
  tone.
- Store such an image losslessly on import instead of re-encoding it to JPEG,
  so the level structure survives and, for these pages, the stored blob is
  smaller rather than larger.
- In automatic compression, choose lossless Flate for such a page instead of
  JPEG.
- Leave every other case unchanged: genuinely continuous-tone grayscale and all
  colour pages still use JPEG, bilevel pages still use their bilevel codec,
  images with an alpha channel still use Flate, and the explicit `jpg` and
  `jp2` choices still force their codecs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `image-storage-format`: the continuous-tone storage requirement gains a
  lossless branch for low-colour-depth grayscale images, so the import-time
  JPEG no longer destroys the level structure.
- `pdf-image-compression`: automatic compression gains a Flate branch for
  low-colour-depth grayscale pages, and the "continuous-tone uses JPEG"
  requirement is narrowed to genuinely continuous-tone images.

## Impact

`page.py` (`resolve_pdf_codec`, `to_stored_bytes`) and the import path that
decides the stored format; the size estimate in `savethread.py` already derives
from `resolve_pdf_codec`, so it follows automatically. A per-page distinct-level
count is needed; it is cheap on the already-loaded image and can reuse the
existing per-page statistics pass. Sessions written before the change keep
their JPEG blobs and must stay readable. The threshold that defines "few
levels" is a design decision. Tests in `tests/test_04_page.py` (the
colour-model and codec table) and the storage tests.
