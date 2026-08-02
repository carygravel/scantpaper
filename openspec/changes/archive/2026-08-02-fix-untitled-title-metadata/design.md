## Overview

The `'Untitled'` title is injected into PDFs by Ghostscript during ocrmypdf's
PDF/A conversion, and ocrmypdf's cleanup guard
(`/usr/lib/python3/dist-packages/ocrmypdf/_metadata.py:112`) only matches the
unquoted `Untitled` while this Ghostscript (10.07.1) writes `'Untitled'` with
literal apostrophes. The fix has two complementary parts:

1. **Save-side (root-cause workaround)**: after ocrmypdf finishes, remove the
   title from the output when no title was requested.
2. **Import-side (safety net)**: treat placeholder titles as empty when
   importing any document, which also heals files already saved with the
   placeholder.

## Save-side fix

**Where**: `do_save_pdf` in `scantpaper/savethread.py:100`, after
`ocrmypdf.api._hocr_to_ocr_pdf` returns (line 193) and before `_append_pdf`
(line 198).

**When**: only when no title was requested, i.e. `"title" not in metadata`.
`prepare_output_metadata` (`savethread.py:614`) already omits `title` for empty
input (guard at line 627), so absence of the key is the condition. This keeps
the extra work off the common save-with-title path.

**How**: a new helper (module-level, e.g. `_remove_pdf_title(path)`) using
pikepdf, verified working on the actual `wf/metafix.pdf` artifact:

```python
def _remove_pdf_title(path):
    with pikepdf.open(path) as pdf:
        with pdf.open_metadata(
            set_pikepdf_as_editor=False, update_docinfo=False
        ) as md:
            md.pop("dc:title", None)
        if "/Title" in pdf.docinfo:
            del pdf.docinfo["/Title"]
        pdf.save(path, preserve_pdfa=True, linearize=True)
```

- `pdf.open_metadata()` requires lxml (installed: lxml 6.1.0); the `with` block
  opens the XMP metadata for editing. `md.pop("dc:title", None)` removes the
  `dc:title` element from the XMP stream. Deleting `/Title` from `docinfo`
  handles the document-info entry (also present in the affected output).
- `pdf.save(path, ...)` writes via a temporary file and moves it into place, so
  saving to the same path is safe. `preserve_pdfa=True` keeps the XMP metadata
  stream and PDF/A identification intact; `linearize=True` restores fast web
  viewing. Verified: after the strip, `pdfinfo` reports no `Title:` line, XMP
  has no `dc:title`, and the file remains a valid PDF.
- **Placement rationale**: must run before `_append_pdf` (pdfunite merge, line
  198) so the cleaned title propagates, and before `_encrypt_pdf` (qpdf, line
  200) because pikepdf cannot open a password-encrypted file without the
  password.

**Dependency**: add `pikepdf` to `pyproject.toml` `dependencies`. It is already
present transitively via `ocrmypdf` and already imported by the test suite
(`test_1111_save_pdf.py`, `test_1162_save_multipage_pdf.py`).

**Overhead** (measured): ~5 ms at 0.5 MB, ~35 ms at 12.9 MB, ~0.5 s at 67 MB,
~1.9 s at 104 MB. Against an 8-page pipeline of img2pdf 0.19 s + ocrmypdf
1.78 s this is ≤0.2% and only incurred when no title was requested.

**Side effect**: the PDF `Producer` field changes to `pikepdf <version>` after
the round-trip. Accepted; this matches any pikepdf round-trip and is cosmetic.

**Alternative considered — strip only placeholder titles**: rejected. When no
title was requested, the only title ocrmypdf can produce is the
Ghostscript-injected placeholder; removing the title unconditionally is simpler
and robust to future placeholder variants.

**Out of scope — fix ocrmypdf**: the upstream guard misses the quoted variant
and is unfixed in released ocrmypdf (ocrmypdf issue #582 closed incomplete;
Red Hat bug #2458687 shows upstream's own regression test failing). scantpaper
should still report this upstream, but cannot depend on a fix.

## Import-side fix

**Where**: `_extract_metadata` in `scantpaper/document.py:438`. This is the
single cross-format normalization point (PDF, DjVu, TIFF all flow through it)
and already has the precedent of treating `info[key] != "NONE"` as "no value".
Alternative location `_add_metadata_to_info` (`importthread.py:528`) was
rejected: its capture regex differs per format and normalizing there would be
format-specific.

**How**: a new module-level helper and a guard on the title key:

```python
def _is_placeholder_title(value):
    return value.strip().strip("'").strip().lower() == "untitled"
```

In `_extract_metadata`, exclude a placeholder title from the returned metadata
(checked on the unescaped value, consistent with what gets stored):

```python
if (
    re.search(r"(author|title|subject|keywords)", key, ...)
    and info[key] != "NONE"
    and not (key == "title" and _is_placeholder_title(unescape_utf8(info[key])))
):
    metadata[key] = unescape_utf8(info[key])
```

**Values covered**: `Untitled`, `'Untitled'` (literal apostrophes), case
variants (`untitled`, `UNTITLED`), and surrounding whitespace. Real titles such
as `La Voz de Galicia` pass through unchanged.

**Effect on existing files**: PDFs already saved with the placeholder lose it
on re-import, so the fix heals existing sessions without a migration.

## Testing

- **Save-side** (extend `scantpaper/tests/test_1111_save_pdf.py`): save a PDF
  with no title → open output with pikepdf, assert no `/Title` in docinfo and
  no `dc:title` in XMP metadata; `pdfinfo` reports no `Title:`. Save with a
  title → assert the title is retained exactly.
- **Import-side** (extend
  `scantpaper/tests/test_1622_import_multipage_pdf.py`): feed `_extract_metadata`
  an info dict with `title` = `Untitled`, `'Untitled'`, `UNTITLED` → returned
  metadata has no title; `La Voz de Galicia` → preserved. Extend
  `test_import_pdf_with_metadata` (line 276) with a placeholder-title PDF.
- **Integration**: run a full save (no title) of a real document through the
  pipeline and re-import the output; assert the session title is empty.
