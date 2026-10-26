# Design

## Context

See `proposal.md` for motivation. The constraints that shape the approach:

- `pyproject.toml` declares `ocrmypdf>=16.10.0`, and `packaging/opensuse/`
  deliberately builds OCRmyPDF 16.11.1, the newest whose dependencies exist on
  Leap 16.0. The fix must work across that range, not only on current releases.
- `savethread.do_save_pdf` assembles `origin.pdf` with img2pdf, then calls
  `ocrmypdf.api._hocr_to_ocr_pdf(outdir, filename, optimize=0, plugins=[...])`
  in `_embed_text_layer`. OCRmyPDF grafts the text layer and produces PDF/A,
  invoking Ghostscript, which may transcode images.
- OCRmyPDF's `pdfa_image_compression` value is document-wide (one value per
  conversion), and its `auto` default changed meaning in 17.6: at `-O0`,
  `auto` now keeps lossless images, while before 17.6 it deferred to
  Ghostscript's lossy heuristic. The `lossless` value exists in both ranges,
  but before 17.6 it re-encodes an existing JPEG losslessly (inflating it).

## Goals / Non-Goals

**Goals:**

- A losslessly written page image is not transcoded to a lossy codec by the
  PDF/A conversion, on every supported OCRmyPDF version.
- A JPEG-only save is not needlessly inflated on older OCRmyPDF.

**Non-Goals:**

- Changing scantpaper's own codec choice for a page; that is
  `flate-for-low-colour-grayscale`.
- Supporting OCRmyPDF below the declared floor.
- Replacing PDF/A output or the Ghostscript conversion.

## Decisions

### Decision: request `pdfa_image_compression="lossless"` explicitly, version-gated

Pass the option explicitly rather than inherit `auto`, because `auto`'s
meaning is version-dependent. Gate the value on the installed OCRmyPDF:

- **OCRmyPDF >= 17.6**: always request `lossless`. Lossless images are kept and
  existing JPEGs pass through unchanged, so both guarantees hold for every
  document, mixed or not.
- **OCRmyPDF < 17.6**: request `lossless` only when the save wrote at least one
  non-JPEG page image. When every page image is JPEG, leave the option unset so
  OCRmyPDF's `auto` keeps the JPEGs rather than re-encoding them losslessly.

version detection parses `ocrmypdf.__version__` (already logged in
`app_window`) into its leading `(major, minor)` components. An unparseable or
unexpected version is treated as the `< 17.6` branch, which still protects
lossless images and still avoids inflating JPEG-only saves.

Alternatives considered:

- **Unconditional `lossless`**: rejected. On OCRmyPDF 16.x it re-encodes every
  JPEG page losslessly, a large size regression for the most common scan.
- **Require `ocrmypdf>=17.6`**: rejected. It drops the openSUSE 16.11
  packaging target and any distro on 16.x, for a bug that a small branch fixes.
- **Skip PDF/A (`--output-type pdf`)**: rejected. It removes a documented,
  user-visible output characteristic.

### Decision: track "any non-JPEG image" during assembly

`_assemble_pdf` already resolves each page's codec through
`write_image_for_pdf` and `_estimate_page_pdf_size`. Record there whether any
page image was written with a non-JPEG codec, and read the flag in
`_embed_text_layer`, which runs immediately afterwards.

Re-deriving the codecs inside `_embed_text_layer` was rejected: pages are
loaded and released one at a time during assembly, so re-deriving would reload
every page.

## Risks / Trade-offs

- **Mixed lossless+JPEG document on OCRmyPDF < 17.6** re-encodes the JPEG pages
  losslessly, enlarging them, because the option is document-wide. Mitigation:
  favour image quality over size in that corner; the spec scopes the JPEG
  guarantee to JPEG-only saves, and the situation does not arise on >= 17.6.
- **Version parsing fragility** for pre-release or patched version strings.
  Mitigation: compare only the leading numeric components and fall back to the
  conservative `< 17.6` branch when parsing fails.
- **Passing the option selects Ghostscript** on newer OCRmyPDF builds where a
  speculative PDF/A path exists. Mitigation: none needed - the conversion
  already runs Ghostscript on the versions scantpaper targets, and PDF/A
  correctness is unchanged.
