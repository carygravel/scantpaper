## Context

See proposal.md - Why. The PDF compression menu is built from
`PDF_COMPRESSION_ALGS` in `dialog/save.py`; the selected option is
persisted as the `pdf compression` setting and resolved to a concrete
codec by `resolve_pdf_codec` in `page.py`. `resolve_pdf_codec` maps the
`lzw` option to Flate and the `g3` option to Group 4, so both menu entries
are aliases of options that already exist under honest names. The TIFF
compression menu independently uses `lzw` and `g3` for its own, genuine
LZW and CCITT Group 3 encodings, so those strings must stay.

## Goals / Non-Goals

**Goals:**

- Remove the redundant/misleading PDF **LZW** and **G3** choices.
- Keep a user's existing output stable: a stored `lzw`/`g3` PDF
  preference keeps producing Flate/Group 4 and leaves the combo with a
  valid selection.
- Keep the TIFF LZW/G3 choices and their translations untouched.

**Non-Goals:**

- No new compression codecs, no change to automatic selection or the
  bilevel codec preference.
- No removal of the LZW/G3 msgids (the TIFF menu still references them).

## Decisions

- **Scope the removal to the PDF menu only.** The LZW/G3 options are
  honest and useful for TIFF (`tiffcp -c lzw|g3`); only the PDF entries
  are aliases. Alternative of removing both would remove real
  functionality and force the TIFF menu to change, out of scope.
- **Migrate `lzw` → `png` and `g3` → `g4` in the config loader.** The
  migration targets are the *option keys* (Flate is keyed `png`, Group 4
  is keyed `g4`), not the codec constants (`flate`/`g4`). Mapping to those
  keys preserves the exact stream each setting produced before and leaves
  the combo with a selectable row. Alternative of rewriting both to
  `auto` would change output for bilevel pages (e.g. `lzw` used to force
  Flate even for bilevel) and was rejected. The mapping is unconditional
  and idempotent, so it needs no version gate (unlike the threshold
  migration, which rewrites a numeric scale).
- **Migrate in `config._deserialise_and_migrate`, not in the resolver or
  the dialog.** A single load-time migration covers every consumer of
  `settings["pdf compression"]`. Alternative of sanitising inside the save
  dialog would leave the persisted value stale and would miss the
  non-dialog save paths.
- **Drop the `g3` alias from `resolve_pdf_codec`.** `lzw` already reached
  Flate through the generic non-`auto` fallback, so no code changes there;
  only the `("g3", "g4")` tuple becomes `"g4"`. This keeps the resolver in
  step with the offered option set.
- **Recompute `_JBIG2_ALG_INDEX`** from 4 to 2 so JBIG2 is still inserted
  directly after Group 4 in the shorter list.

## Risks / Trade-offs

- [A `g3`/`lzw` value reaches `resolve_pdf_codec` without passing through
  the config loader (e.g. settings injected directly)] → The resolver's
  non-`auto` fallback still yields Flate for `lzw`; a stray `g3` would now
  yield Flate instead of Group 4. The load-time migration is the
  mitigation for the only real source (a persisted config); unit tests
  pin the migration.
- [Test churn] → A few PDF tests and the compression-callback tests use
  `lzw`/`g3`; update them to `g4`/`png`. TIFF tests keep `lzw`.
- [Translation drift] → None expected: TIFF keeps the `LZW`/`G3`/Group 3
  msgids, so the catalogs and `check_po.py` are unaffected.

## Migration Plan

The config loader maps `lzw` → `png` and `g3` → `g4` on read; no user
action. The change is one-way but safe to roll back: an older version
reads `png`/`g4` as its Flate/Group 4 options.
