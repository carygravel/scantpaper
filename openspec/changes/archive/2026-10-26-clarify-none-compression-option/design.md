# Design

## Context

See `proposal.md` for motivation. `dialog/save.py` defines
`PDF_COMPRESSION_ALGS`, which includes `("none", _("None"), ...)`, and
`resolve_pdf_codec` maps both `none` and `png` to Flate, so the two choices
produce the same codec. `config._migrate_pdf_compression` already rewrites the
removed `g3` and `lzw` preferences. The stored default is `auto`, so most users
are unaffected. `pdf_compression_algs()` presents the list and inserts the
availability-gated `jb2` entry after Group 4.

## Goals / Non-Goals

**Goals:**

- Remove the mismatch between the "None" label and its Flate behaviour.
- Keep a single, honest lossless choice.
- Preserve the output of a user who had stored `none`.

**Non-Goals:**

- Giving "None" a distinct raw/uncompressed meaning. PDF has no useful
  uncompressed image form here, and no scantpaper code path emits one.
- Changing what the Flate option means.

## Decisions

### Decision: remove the "None" choice

Remove `("none", ...)` from `PDF_COMPRESSION_ALGS`. It resolves to the same
codec as the Flate entry while its label promises no compression and no
re-encoding. Relabelling it was rejected: it would still duplicate Flate.
Giving it a raw meaning was rejected: uncompressed bitmaps are large and
unsupported by the assembly path.

### Decision: migrate a stored `none` preference to `png`

Extend `_migrate_pdf_compression` so a loaded `none` becomes `png`, mirroring
`g3 -> g4` and `lzw -> png`. The user keeps the lossless Flate output and the
menu shows a valid entry. Leaving the value as `none` was rejected: the menu
would show no selection and the stored value would be stale.

## Risks / Trade-offs

- A user who selected "None" now sees "Flate". The output bytes are identical,
  so only the label changes; the migration preserves behaviour.
- The `jb2` entry is inserted at a fixed index after Group 4, not after the
  removed `none`. Mitigation: a test asserts the resulting option order.
