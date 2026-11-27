# Design

## Context

See `proposal.md` - Why. `_embed_text_layer()` calls
`ocrmypdf.api._hocr_to_ocr_pdf()`, which runs OCRmyPDF's fpdf2 renderer to
draw the invisible text layer onto each page image. The renderer calls
`FPDF.set_text_shaping(True)`; fpdf2 then enables the `liga` feature by
default, so `ff` becomes a single glyph. The generated PDF maps that glyph to
the two characters through a multi-character `ToUnicode` range
(`<0006><0006><00660066>`).

Ghostscript 10.06 (Ubuntu 26.04) rebuilds the font when it produces PDF/A and
drops that multi-character range, leaving `<0006><0006><0066>` absent from the
CMap entirely. Text extraction then loses the whole word. Ghostscript 10.08
(Debian sid and the development host) keeps the range, which is why the same
test passes everywhere but 26.04.

## Goals / Non-Goals

**Goals:**

- Keep every character of the text layer searchable on every supported
  Ghostscript version.
- Leave the visible page image untouched; only the invisible text layer
  changes.
- Preserve any shaping features a caller specifies explicitly.
- Keep the save working on OCRmyPDF releases without the fpdf2 renderer.

**Non-Goals:**

- Changing the emitted hOCR, the stored text layer, or the page image.
- Patching Ghostscript or requiring a newer release on 26.04.
- Disabling shaping altogether: direction and script handling are still
  needed for right-to-left text.

## Decisions

### Disable only the ligature feature

Wrapping the OCRmyPDF call in a context manager replaces
`FPDF.set_text_shaping` for the duration of the graft. When shaping is
enabled and the caller passes no feature set, the wrapper adds
`features={"liga": False}`. The letters are then drawn individually, each with
its own single-character `ToUnicode` entry, which Ghostscript 10.06 preserves.

Alternatives considered:

- **Pass a different OCRmyPDF option.** OCRmyPDF exposes no option for
  shaping features. Rejected.
- **Disable shaping entirely.** That would drop the direction and script
  handling needed for non-Latin text. Rejected.
- **Patch the generated PDF afterwards.** The lost mapping is already gone
  from the PDF/A output, and reconstructing it would require guessing which
  glyphs formed a ligature. Rejected.

### Load fpdf2 when the save module is imported

The wrapper needs the `fpdf` module. Importing it lazily is unsafe in this
codebase because a test replaces `scantpaper.savethread.pathlib.Path`, which
mutates the global `pathlib` module. If fpdf2 is first imported during that
test, it computes `FPDF_FONT_DIR` from the mock and later font lookups fail.
`_load_fpdf()` runs at module import instead, returning `None` when the
package is absent.

### Wrap only the hOCR-to-PDF call

The fpdf2 renderer is used only inside `_hocr_to_ocr_pdf()`. Restoring the
original method in a `finally` keeps the patch scoped to that call and leaves
other OCRmyPDF work unaffected.

## Risks / Trade-offs

- [Disabling ligatures changes the invisible text layout] -> The rendered
  page is unchanged; extraction returns the same characters.
- [A future OCRmyPDF changes the renderer API] -> The wrapper only intercepts
  `set_text_shaping`; when the method or module is absent the save proceeds
  unchanged, and the test matrix would show a regression.
- [Eager fpdf2 import adds start-up cost] -> The module is already imported
  transitively by OCRmyPDF when it is available, and the import is still
  optional.

## Migration Plan

None. The change applies at save time; existing sessions save correctly on
the next save. Reverting restores the previous rendering without altering
stored data.

## Open Questions

None.
