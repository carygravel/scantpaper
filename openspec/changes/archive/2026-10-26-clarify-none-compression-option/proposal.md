# Proposal

## Why

The save dialog offers a PDF compression choice labelled "None - Use no
compression algorithm on output". It does neither. `resolve_pdf_codec` maps the
`none` value to lossless Flate, the same codec as the separately offered Flate
(`png`) choice, so "None" is a duplicate of "Flate" under a name that promises
something else. The mismatched reading cuts both ways: a user who picks "None"
to embed the page without re-encoding still gets a Flate re-encode, and a user
who expects literally uncompressed output never gets it. A user report showed
the confusion directly: they chose "None" to avoid re-encoding a TIFF page and
could not understand the result.

## What Changes

- Resolve the mismatch by removing the redundant "None" PDF compression choice,
  which is behaviourally identical to Flate. If design prefers to keep it, it
  must instead carry a truthful label and description; removing is the
  recommended direction, because a duplicate that lies is worse than an absent
  choice.
- Migrate a stored `pdf compression` preference of `none` to `png`, so the user
  keeps the lossless Flate output they already had and the menu shows a valid,
  honest selection. This mirrors the existing migration of the removed `g3` and
  `lzw` preferences.
- Leave the remaining choices and the codecs they resolve to unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pdf-image-compression`: the selectable-options requirement drops the "None"
  choice (or gains a precise, truthful definition of it), and the preference
  migration requirement maps a stored `none` to `png` alongside the existing
  `g3` and `lzw` migrations.

## Impact

`dialog/save.py` (`PDF_COMPRESSION_ALGS`, `pdf_compression_algs`), the config
migration in `config.py` next to `_migrate_pdf_compression`, and the save
settings that read the choice in `file_menu_mixins.py` and
`tools_menu_mixins.py`. Tests in `tests/test_dialog_save.py` and the
config-migration tests. User-visible: the compression dropdown and the meaning
of a stored preference.
