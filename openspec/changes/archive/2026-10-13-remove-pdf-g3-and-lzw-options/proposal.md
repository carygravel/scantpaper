## Why

The PDF compression menu offers **LZW** and **G3**, but neither does what
its label promises. `resolve_pdf_codec` maps the `lzw` option to lossless
Flate (identical to the separate **Flate** entry) and the `g3` option to
CCITT Group 4 (identical to the separate **G4** entry). The two entries are
therefore duplicates that misdescribe the output, and they were the only
reason the README's Save section still listed "LZW" and "G3".

## What Changes

- Remove the **LZW** and **G3** entries from the PDF **Compression** menu
  (the TIFF compression menu keeps its native LZW/G3 choices).
- Migrate a stored `pdf compression` setting of `lzw` to the Flate option
  (`png`) and `g3` to `g4`, so a configuration written before this change
  keeps the exact output it produced before (Flate / Group 4) instead of
  leaving the combo with no valid selection.
- Drop the now-unreachable `g3`/`lzw` PDF resolution cases; `resolve_pdf_codec`
  keeps handling `g4`, `jpg`, `jp2`, `jb2`, `png`/`none` and `auto`.
- Update the README Save section to list the PDF compression options without
  LZW and G3.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `pdf-image-compression`: the set of explicit PDF compression options no
  longer includes G3 or LZW; the "Explicit compression options honoured"
  and "Bilevel pages encoded as Group 4" requirements drop their `lzw`/`g3`
  references (Flate is selected by the `png` option, Group 4 by `g4`).

## Impact

- `src/scantpaper/dialog/save.py`: `PDF_COMPRESSION_ALGS` (remove two rows),
  `_JBIG2_ALG_INDEX` (recomputed for the shorter list).
- `src/scantpaper/page.py`: `resolve_pdf_codec` (drop the `g3` alias; `lzw`
  no longer resolves via the menu).
- `src/scantpaper/config.py`: a migration for stored `pdf compression`
  values `lzw`/`g3`.
- `README.md`: Save section option list.
- Tests: `test_04_page.py`, `test_dialog_save.py`, `test_052_dialog_save.py`,
  and the config migration tests.
- No dependency or packaging changes; no translatable string is removed
  because the TIFF menu still uses the same "LZW"/"G3" msgids.
