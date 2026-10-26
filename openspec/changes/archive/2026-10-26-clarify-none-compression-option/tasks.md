# Tasks

## 1. Remove the choice and migrate the preference

- [x] 1.1 Remove the `none` entry from `PDF_COMPRESSION_ALGS`; verify with a
  unit test that `pdf_compression_algs()` lists Automatic, G4, Flate, JPEG and
  JPEG 2000 in order (plus JBIG2 when available) and no `none`.
- [x] 1.2 Extend `_migrate_pdf_compression` to map `none -> png`; verify with a
  config-loading test that a stored `none` becomes `png`.

## 2. Documentation

- [x] 2.1 Update `README.md` where the compression options are described;
  verify the documented list matches `pdf_compression_algs()`.

## Workflow follow-up

- Archive the change once review is complete.
