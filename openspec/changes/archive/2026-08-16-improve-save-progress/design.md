## Context

`do_save_pdf()` (savethread.py:101-225) currently reports per-page progress ("Saving page i of n" + fraction) only in the hocr text-write loop that runs *after* `img2pdf.convert()`. The stage that actually dominates wall time — the image-write loop that PNG-encodes each page into a tempdir (savethread.py:126-138) — sends no progress at all. The `data_callback` wiring already exists (file_menu_mixins.py:641 wires `post_process_progress.update`, which renders DATA strings as text and floats as fraction — progress.py:82-88), so this is purely about *what* the thread emits.

The DjVu save path (`do_save_djvu`, savethread.py:233-248) already shows the intended pattern: per-iteration `request.data(fraction)` followed by `request.data(_("Writing page %i of %i"))`.

Cancellation is out of scope: the post-process progress bar's cancel button only hides the bar (`slist.cancel` is commented out at progress.py:67-74), so no real cancel signal is ever sent to a save request.

## Goals / Non-Goals

**Goals:**
- Report per-page fraction + message from the image-write loop, mirroring the DjVu pattern.
- Report a stage message during `img2pdf.convert()`.
- Remove the misleading per-page reporting from the hocr loop so the bar reflects work actually in progress.
- Keep the change confined to `do_save_pdf()` and its tests.

**Non-Goals:**
- Wiring up real cancellation for saves (progress.py's cancel button is cosmetic for post-process ops).
- Smooth fraction accounting across the img2pdf → ocrmypdf boundary (ocrmypdf's plugin already restarts its own fraction from ~0 today; no regression).
- Fixing the underlying PNG-encode cost or image format choices — tracked separately.

## Decisions

**1. Per-page progress goes in the image-write loop, 1-based `i` with `i / (len + 1)` fractions.**
Mirrors `do_save_djvu` exactly: `i` is incremented per page, fraction is `i / (len(args["list_of_pages"]) + 1)`, message is `_("Writing page %i of %i")`. The `+1` in the denominator reserves headroom so the bar never pins at 1.0 before the final `request.data(1.0)` (line 196).
- Alternative considered: computing fractions as `pagenr / len` (0-based). Rejected — inconsistent with the DjVu/TIFF paths and existing tests.

**2. "Writing PDF" message before `img2pdf.convert()`.**
Insert `request.data(_("Writing PDF"))` immediately before line 150. The fraction stays where the write loop left it (~1.0) while the message signals conversion is happening. Alternative: pulsing — rejected, no established pulse usage in this path, and the message is clearer.
- Note: the string is deliberately short (matches the "Setting up PDF" style at line 105) rather than "Writing PDF…", to avoid needing an ellipsis character in the .po files.

**3. Delete the hocr-loop per-page reporting (lines 171-178), keep `check_cancelled()`.**
The "Embedding text layer" message (line 182) and ocrmypdf's `SaveThreadProgressBar` already cover the post-conversion phase. `check_cancelled()` (line 179) stays where it is — harmless, pre-existing, and no real cancel is ever sent.

**4. Reuse the existing "Writing page %i of %i" translation.**
The string is already in the .po files via the DjVu path. Only the new "Writing PDF" string needs a po entry, regenerated via `dev/generate_pot.py`.

## Risks / Trade-offs

- **Fraction jumps backward when ocrmypdf starts** → pre-existing behavior (the hocr loop already sent 0..~0.95 before ocrmypdf restarted from ~0); explicitly a non-goal.
- **Hocr loop becomes silent** → acceptable: it's fast, and the following "Embedding text layer" message plus ocrmypdf's plugin progress cover the phase. Existing tests that assert hocr-loop progress messages must be updated (test_1111_save_pdf.py, specifically the progress-hook tests around line 841+).
