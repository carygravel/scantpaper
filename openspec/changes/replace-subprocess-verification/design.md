## Context

The test suite verifies output correctness by shelling out to CLI tools (pdfinfo, identify, cat, etc.). This worked when the project was Perl-based, but the Python rewrite already has pikepdf and Pillow as dependencies — both of which can query the same properties these tools check. Replacing subprocess calls with library calls removes process-spawn overhead and makes tests easier to debug (no parsing CLI output).

## Goals / Non-Goals

**Goals:**
- Replace all `cat` calls with Python file reads
- Replace all `pdfinfo` calls with pikepdf queries
- Replace all `identify` calls with PIL.Image queries
- Maintain identical assertion coverage (same properties checked)
- Keep total test time ≤ 98s

**Non-Goals:**
- Replacing pdftotext, pdfimages, pdffonts, djvu tools, gs, or convert calls (no viable Python replacements)
- Modifying setup subprocess calls (convert, tiffcp, touch, ln)
- Refactoring test structure or fixtures (that's a separate change)
- Changing what properties are tested

## Decisions

### Use pikepdf for PDF metadata (page size, page count, encryption, dates)

pikepdf is already a dependency and exposes MediaBox, page count, and metadata via a clean Python API. It cannot extract text from hOCR PDFs, so `pdftotext` calls stay as subprocess.

For page size: read `page.MediaBox` and compute width/height.
For page count: `len(pdf.pages)`.
For encryption: wrap `pikepdf.open()` in try/except for `PasswordError`.
For metadata: `pdf.docinfo` dict.

### Use PIL.Image for image properties (dimensions, format, bit depth, color space)

Pillow is already a dependency. For each `identify` call, open the image with `PIL.Image.open()` and assert on `.size`, `.format`, `.mode`, `.bits`.

For TIFF-specific checks (group4 compression, rows-per-strip), use `tifffile` or keep subprocess since PIL doesn't expose all TIFF tags reliably.

For pdfimages extraction → identify pipeline: keep as subprocess since pdfimages output is an intermediate artifact.

### Keep file reads for text verification

Replace `subprocess.check_output(["cat", path])` with `open(path).read()`. Trivial and eliminates 12 subprocess calls.

## Risks / Trade-offs

- **Risk**: Some `identify` format strings check properties PIL doesn't expose (e.g., `%g` geometry, `%z-bit` depth for specific formats). **Mitigation**: Keep subprocess for those specific calls; only replace where PIL covers the property.
- **Risk**: pikepdf page size parsing may differ slightly from pdfinfo output format. **Mitigation**: Use `pytest.approx()` for floating-point comparison instead of regex matching.
- **Trade-off**: Converting regex-based assertions to Python property assertions is more verbose but more readable and debuggable.
