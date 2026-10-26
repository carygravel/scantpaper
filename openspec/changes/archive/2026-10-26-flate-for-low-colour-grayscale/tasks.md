# Tasks

## 1. Predicate and constant

- [x] 1.1 Add `LOW_COLOUR_DEPTH_LEVELS` to `const.py` and a grayscale
  low-colour-depth predicate to `page.py`; verify with unit tests over 1-, 8-,
  16- and 256-level grayscale images (boundary at 16) and an RGB image that is
  never treated as low colour depth.

## 2. Lossless storage

- [x] 2.1 Use the predicate in `to_stored_bytes` so a low-colour-depth
  grayscale image is stored as PNG; verify the stored blob is PNG and
  reproduces the exact intensity levels, extending the storage tests.

## 3. Lossless save codec

- [x] 3.1 Use the predicate in `resolve_pdf_codec` so automatic compression
  resolves a low-colour-depth grayscale page to Flate; verify by updating the
  codec table test and adding a save test whose output page image is Flate.

## 4. Documentation

- [x] 4.1 Note in `README.md` that posterised/low-colour-depth grayscale pages
  are stored and saved losslessly; verify the statement matches the tests.

## Workflow follow-up

- Archive the change once review is complete.
