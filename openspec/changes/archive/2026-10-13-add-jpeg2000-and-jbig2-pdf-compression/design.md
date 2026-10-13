## Context

See `proposal.md` for motivation. Current state that shapes the approach:

- `resolve_pdf_codec` (`page.py:68`) is the single place a compression
  option becomes a concrete codec; `write_image_for_pdf` (`page.py:470`)
  then writes a temp file whose *content* `img2pdf` detects — the file's
  suffix is ignored. Verified: JPEG 2000 bytes written to the existing
  `.png`-suffixed temp file are embedded as `jpx`, so no temp-file naming
  change is needed.
- The save dialog exposes the compression choice via `PDF_COMPRESSION_ALGS`
  (`save.py:45`) and a quality spin-button (`save.py:731`) currently shown
  only for `jpg`.
- The output pipeline is `write_image_for_pdf` → `img2pdf` → `ocrmypdf`
  PDF/A-2 pass (`pdfa_part='2'`) → `pikepdf`. A `.jp2` stream embeds as
  JPXDecode and survives the PDF/A pass intact (verified).
- `_estimate_page_pdf_size` (`savethread.py:751`) runs *after* the image is
  written, so it can stat the actual stream that will be embedded.
- Bilevel pages are written as CCITT Group 4 (`_to_bilevel().save(...
  format="PPM")`), which `img2pdf` transcodes to G4. `img2pdf` **rejects**
  JBIG2 input in both raw and `--pdf` forms (verified), so JBIG2 cannot use
  the `write_image_for_pdf` path.
- OCRmyPDF exposes bitonal-only JBIG2 helpers
  (`ocrmypdf.optimize.extract_images_jbig2` and `convert_to_jbig2`) that
  shell out to `jbig2 --pdf` and rewrite the image stream in place with
  `filter=/JBIG2Decode`. Measured end to end: G4 2428 B → JBIG2 1340 B on a
  300 dpi A4 bilevel page, and the JBIG2 stream survives PDF metadata
  fixup.
- **Correction found during implementation.** Running the JBIG2 pass
  *before* `_embed_text_layer` does **not** survive: OCRmyPDF's embed step
  runs Ghostscript for PDF/A (`try_auto_pdfa`/`convert_to_pdfa`), which
  re-encodes the bilevel image back to CCITT Group 4 — reverting an
  earlier JBIG2 conversion (verified: `origin.pdf` JBIG2 `/JBIG2Decode` 1340 B
  → OCR'd output `/CCITTFaxDecode` 2428 B, for both inline and XObject
  images and at every `optimize` level). Running the pass *after*
  `_embed_text_layer` preserves JBIG2 (verified through the subsequent
  `_fix_pdf_metadata`). The one caveat: Ghostscript inlines very small
  images, so the post-embed pass cannot reach them; JBIG2 savings on such
  images are negligible and the page correctly stays Group 4.
- User preferences live in a `ConfigDict` (`config.py`) with
  `DEFAULTS` filled in by `add_defaults`; the Preferences dialog
  (`dialog/preferences.py`) edits and persists them. A new preference
  key is therefore just a `DEFAULTS` entry plus a combo-box.
- The post-assembly JBIG2 pass rewrites *all* bilevel CCITT streams in
  the OCR'd PDF. Compression is a single per-save choice, so a save
  is homogeneous (whole document `auto` + preference, or one explicit
  option); the pass never mixes intentions.

## Goals / Non-Goals

**Goals:**

- Add JPEG 2000 (`jp2`) as an explicit PDF compression option.
- Add JBIG2 (`jb2`) as an availability-gated bilevel option.
- Add a bilevel codec preference (`g4`/`jb2`) that guides `auto` bilevel
  pages, defaulting to Group 4.
- Preserve the existing colour-model rules under `jp2` and `jb2`
  (bilevel → Group 4, alpha → Flate).
- Reuse the existing quality control to steer JPEG 2000 output.
- Keep the size estimator accurate for JPEG 2000 pages.
- Leave `auto` and every existing default byte-for-byte unchanged when
  the bilevel preference is its default.

**Non-Goals:**

- Making JPEG 2000 or JBIG2 the default; the bilevel preference defaults
  to Group 4, so existing output is unchanged out of the box.
- Lossless JPEG 2000 (larger than Flate for documents).
- Lossy JBIG2 (removed from OCRmyPDF for character-substitution risk).
- Bundling or vendoring `jbig2enc`; the binary is used if present.
- Context-dependent bilevel codecs (e.g. a per-document or size-based
  auto-switch); the preference is a single user-wide choice.
- JPEG 2000 or JBIG2 for DjVu output (the `c44`/`cjb2` paths are unchanged).

## Decisions

### Decision: Resolve `jp2` through the colour-model rules

Add a `PDF_CODEC_JP2 = "jp2"` constant. In `resolve_pdf_codec`, handle
`jp2` (and the alias `jpeg2000`) *before* the generic explicit-option
branch, returning Group 4 for bilevel, Flate for alpha, and JPEG 2000
otherwise.

- Why: a plain "explicit option → constant codec" mapping would embed a
  bilevel or transparent image as JPEG 2000, contradicting the spec's
  colour-model rules.
- Alternative considered: reuse the `auto` branch with JPEG swapped for
  JPEG 2000. Rejected as less explicit; the dedicated branch reads clearly.

### Decision: Encode lossy JPEG 2000 via Pillow

In `write_image_for_pdf`, a JPEG 2000 page is written with
`image.save(filename, format="JPEG2000", irreversible=True,
quality_mode="rates", quality_layers=[rate])`. Modes Pillow cannot write
as JPEG 2000 (`P`, `I`) are converted the same way `_encode_jpeg` does
(`P`→`RGB`, `I`→`L`).

- Why: OpenJPEG is the only available encoder and is reached through
  Pillow; `irreversible=True` selects lossy compression.
- Alternative considered: lossless JPEG 2000. Rejected — measured larger
  than Flate for text (5.26 MB vs 4.76 MB on a 300 dpi A4 page).

### Decision: Map the quality spin-button to a JPEG 2000 rate

Reuse the existing 1–100 quality value as
`rate = max(1, round((100 - quality) * 0.32) + 1)`, so the default
quality (75) lands near rate 8 — measured at ~37.5 dB, comparable to JPEG
at quality 75 on the same page. Higher quality yields a lower rate
(less compression, larger file), matching the spin-button's direction.

- Why: one control, no new UI, and the direction of "higher is better"
  matches JPEG so the label generalises.
- Alternative considered: a separate JPEG 2000 ratio control. Rejected as
  extra UI for an opt-in feature.
- Alternative considered: `quality_mode="dB"`. Rejected — rate maps more
  directly to the size the user is trading for.

### Decision: Do not passthrough original images for `jp2`

The verbatim passthrough stays gated on `codec == PDF_CODEC_JPEG` and
`auto`, so a JPEG 2000 page always re-encodes from decoded pixels.

- Why: the stored stream is JPEG; embedding it under a JPEG 2000 selection
  would violate the spec and mislead the user.

### Decision: Estimate JPEG 2000 page size from the written stream

`_estimate_page_pdf_size` returns the written temp file's size whenever
the resolved codec embeds that stream verbatim, keying the check off the
resolved compression rather than the stored image's `image.format`.

- Why: JPEG 2000, like JPEG, is embedded verbatim, so the on-disk size is
  the exact PDF contribution and the existing pixel-data fallback would
  overestimate.

### Decision: UI surfaces the option and relabels the quality control

Add `("jp2", _("JPEG 2000"), ...)` to `PDF_COMPRESSION_ALGS`, relabel the
quality label from "JPEG Quality" to "Quality", and show the spin-button
for both `jpg` and `jp2`.

### Decision: Resolve `jb2` through the colour-model rules

`resolve_pdf_codec` maps `jb2` to Group 4 for bilevel, Flate for alpha and
JPEG for continuous-tone — identical to `auto`. The bilevel Group 4 stream
is then upgraded to JBIG2 by a later pass.

- Why: only bilevel pages benefit from JBIG2, so `jb2` should differ from
  `auto` in exactly one respect and leave every other page on the proven
  path. It also means the writer side needs no new encoding code.
- Alternative considered: a `jb2` codec that writes JBIG2 directly.
  Rejected — `img2pdf` rejects JBIG2 input.

### Decision: Convert to JBIG2 in a targeted pass after the text layer

After `_embed_text_layer` writes the OCR'd PDF, a new step — run only for a
`jb2` save (explicit, or `auto` with the `jb2` preference) — opens it with
pikepdf and reuses OCRmyPDF's bitonal-only helpers (`extract_images_jbig2`
+ `convert_to_jbig2`) to replace bilevel Group 4 streams with lossless
JBIG2. It runs *after* the embed step, because OCRmyPDF's PDF/A conversion
(Ghostscript) re-encodes images and would otherwise undo the conversion
(see Context); it runs *before* `_finalize_pdf`, so metadata, appending,
encryption and PostScript conversion still see the final streams.

- Why: it touches only bitonal images, so continuous-tone pages keep the
  JPEG quality the user selected. Placing it after OCRmyPDF is required for
  the JBIG2 stream to reach the output file at all.
- Alternative considered: run before `_embed_text_layer`, as the design
  first proposed. Rejected — empirically reverted to CCITT by the PDF/A
  pass.
- Alternative considered: pass `optimize=1` to
  `ocrmypdf.api._hocr_to_ocr_pdf`. Rejected — the whole optimizer also
  recompresses JPEG and PNG images (`transcode_jpegs`, `transcode_pngs`),
  overriding the user's JPEG quality and causing an extra lossy
  generation, and it still runs before the images are re-encoded by the
  PDF/A step in our pipeline.
- Alternative considered: reimplement the stream replacement in
  scantpaper. Rejected as duplication of tested library logic that already
  handles colours, masks and Decode tables.

### Decision: Gate `jb2` on encoder availability

Availability is detected once per save via the `jbig2` binary probe
(shell `which`/version check, matching OCRmyPDF's `jbig2enc.available()`).
The `jb2` entry is added to `PDF_COMPRESSION_ALGS` only when available, so
older Ubuntu, Fedora and stock Arch simply do not show it. A stale `jb2`
request without the encoder still resolves to Group 4, so a save never
fails.

- Why: matches the packaging reality and keeps the menu honest.
- Alternative considered: always show `jb2` and warn on use. Rejected —
  offering an option that silently degrades to G4 is worse than omitting
  it.

### Decision: Bilevel codec preference guides `auto`, defaulting to Group 4

Add a `"bilevel compression"` key to `config.DEFAULTS` with value `g4`
(Group 4) or `jb2`. At save time the effective bilevel codec for `auto`
is the preference when it can be honoured: an `auto` save with the
preference `jb2` and the encoder present behaves like a `jb2` save for
bilevel pages, so the existing targeted JBIG2 pass runs; otherwise the
bilevel codec is Group 4, exactly as today. The preference never
changes how Flate (alpha) and JPEG (continuous-tone) are resolved under
`auto`.

The Preferences dialog (tabular, `_add_general_options2`) gains a
two-entry combo ("Group 4", "JBIG2") whose `jb2` entry is present only
when the encoder probe succeeds, mirroring the save menu.

- Why: it is a single user-wide default for how `auto` handles bilevel,
  defaulting to today's behaviour, and reuses the exact machinery of the
  explicit `jb2` option (resolve-to-G4 + post-assembly pass), so there is
  no new encoding path.
- Why not trace through a per-save checkbox in the save dialog: the save
  dialog already offers `jb2` explicitly; the preference exists so users
  get the behaviour *without* touching the save dialog every time.
- Alternative considered: making the preference switch `auto` to JBIG2
  opportunistically (when present, regardless of user choice). Rejected —
  it would change output based on which machine saved the file, the
  determinism problem the proposal explicitly avoids.
- Alternative considered: nothing — JBIG2 only via the explicit option.
  Rejected at the user's request; the ~2× bilevel win is worth a
  one-time preference.

## Risks / Trade-offs

- [~1 s/page encode cost makes long saves slow] → Opt-in only; the save
  already runs off the main thread with progress and cancellation.
- [Narrower viewer support for JPX than baseline JPEG] → The option is
  explicit; document the trade-off in `README.md`.
- [OpenJPEG may reject some colour modes (e.g. CMYK)] → Wrap the encode in
  `try/except OSError` and fall back to lossless Flate so a save never
  fails on an unsupported mode.
- [OpenJPEG output varies by library version, making byte-size assertions
  flaky] → Tests assert the codec (`pdfimages` reports `jpx`) and relative
  size (low quality < high quality), not absolute byte counts.
- [Reusing `ocrmypdf.optimize` internals couples to a non-public API] →
  Keep the call behind a thin wrapper in one module and cover it with tests
  that skip when the `jbig2` binary is absent; the OCRmyPDF version is
  already pinned.
- [JBIG2 tests cannot run where `jbig2` is missing] → Skip the
  encoder-present scenarios with a clear marker; keep encoder-absent
  behaviour (fallback to Group 4, menu omission) covered unconditionally.
  The CI matrix covers both worlds deliberately: the `latest` and
  `latest_w_ppa` jobs install `jbig2` (available on noble, and already a
  Recommends of the PPA's ocrmypdf), so the encoder-present tests run
  there, while `oldest` (jammy, no package), Fedora and openSUSE exercise
  the encoder-absent path.
- [Quality semantics differ from JPEG] → Document the mapping; no spec
  change implied.
- [New translatable strings] → Run the `generate_pot.py` /
  `check_po.py` workflow; keep msgids short and free of advisories.
- [Preference `jb2` makes output machine-dependent] → The determinism
  concern is avoided by defaulting to `g4` and by honouring the preference
  only when the encoder is present; a user choosing `jb2` has deliberately
  accepted that their files depend on the encoder. Document this in
  `README.md`.

## Migration Plan

- No persisted-state or config migration: the options and preference are
  additive, `auto` keeps its current behaviour at the default, and the new
  `"bilevel compression"` key is filled in by the existing `add_defaults`
  mechanism on next launch. Existing sessions are unaffected.
- Rollback: remove the menu entries, the `resolve_pdf_codec` branches and
  the `"bilevel compression"` key; nothing on disk depends on them.

## Open Questions

- The quality→rate constant (0.32) may want tuning after visual comparison
  against JPEG output; deferrable, and does not change the specs or tasks.
- OCRmyPDF's JBIG2 threshold (default 0.85) may want tuning; it only
  affects bitonal thresholding during encoding and does not change the
  specs or tasks.
