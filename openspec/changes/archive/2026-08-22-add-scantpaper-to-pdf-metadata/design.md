## Context

`do_save_pdf` builds `origin.pdf` with img2pdf (creator branded
`scantpaper v<version>` by `prepare_output_metadata`), then embeds the text
layer via `ocrmypdf.api._hocr_to_ocr_pdf`. ocrmypdf's final metadata stage
discards the input `/Creator` and hardcodes its own toolchain string; there
is no option or plugin hook to change it. After embedding, scantpaper already
re-opens the output with pikepdf when no user title was given
(`_remove_pdf_title`, savethread.py) to strip Ghostscript's placeholder
title, re-saving with `preserve_pdfa=True, linearize=True`.

## Goals / Non-Goals

**Goals:**

- Saved PDFs credit scantpaper first in `/Creator` / `xmp:CreatorTool`,
  keeping the OCR toolchain provenance after it.
- No additional file rewrite in the common save case.
- Document info and XMP stay mutually consistent (PDF/A).

**Non-Goals:**

- Changing `/Producer` or any other metadata field.
- Branding output of pre-/append-to-PDF saves (pdfunite path).
- Changing the DjVu, TIFF or image save paths (DjVu is already branded).

## Decisions

### Post-save pikepdf pass instead of influencing ocrmypdf

ocrmypdf offers neither an option nor a hook for Creator/Producer.
Alternatives considered and rejected:

- *Fake OcrEngine plugin returning a custom `creator_tag`*: semantically
  wrong, risks validation breakage, still leaves OCRmyPDF first in the
  string and Producer untouched.
- *Monkeypatching `ocrmypdf._metadata.get_docinfo`*: fragile across
  versions, worse with Debian's patched `+dfsg` builds.
- *Upstream feature request*: worth pursuing separately, too slow alone.

A pikepdf pass reuses scantpaper's existing dependency and its established
pattern of post-save fixups (`_remove_pdf_title`).

### Prepend to the existing creator string; do not rebuild it

After embedding, read whatever `/Creator` ocrmypdf wrote and prepend
`scantpaper v<version> / `. This yields exactly e.g.
`scantpaper v3.0.16 / OCRmyPDF 16.13.0+dfsg1 / Tesseract OCR-hOCR 5.5.0`
without reconstructing versions ourselves, and tolerates future changes to
ocrmypdf's string format. If the string is missing, fall back to
`scantpaper v<version>` alone. The same value is written to XMP
`xmp:CreatorTool`.

### One merged metadata fixup pass

`_remove_pdf_title` becomes a generalised post-embed pass that removes the
placeholder title when needed and applies creator branding, in a single
open/save cycle. It runs unconditionally on successful embed; the title
removal step remains conditional on no user title being given. Cost: no extra
rewrite when no title was supplied (the pass already happened); one extra
pikepdf open/save only when a user title was provided.

DocInfo/XMP consistency is kept by editing XMP through
`open_metadata(set_pikepdf_as_editor=False)` so pikepdf does not restamp the
producer fields, mirroring the existing title removal code.

### Warn-and-continue on branding failure

If the pikepdf pass fails, log a warning and deliver the unbranded PDF rather
than failing the whole save - matching the existing posture of the embed
fallback path.

## Risks / Trade-offs

- [One extra save pass when a user title was set] → acceptable; linearization
  is required for correctness anyway and large saves are already long.
- [Prepend/append saves go through `pdfunite`, which may not preserve the
  branding] → documented limitation; unchanged behaviour for those modes,
  possible follow-up change.
- [Future ocrmypdf could rename/relocate its metadata stage] → we depend
  only on the finished file's contents, not its internals.
- [Strict PDF/A validators may flag post-conversion edits] → same exposure
  as the existing title removal; `preserve_pdfa=True` is already used there.

## Open Questions

(none)
