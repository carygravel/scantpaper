## Context

`do_scan_page` (frontend/image_sane.py:205) logs `get_parameters()` but
unpacks only the line count, so the delivered depth is discarded; the
PIL mode of the snapped image is the ground truth. The requested depth
lives only in the scan dialog's `current_scan_options` (a Profile whose
backend list holds `(name, value)` pairs, e.g. `("depth", 1)`); it
never travels with the page. `do_threshold` (docthread.py:1307)
already implements the colour-aware conversion and stores a mode-"1"
page; the scan post-process chain (document.py `_post_process_scan`)
currently consumes a `threshold` option only inside `_post_process_ocr`.
See proposal.md for motivation.

Empirical finding (HP Officejet 6500 via hpaio, verified live):
python-sane's `snap()` never returns a mode-"1" image - it hardcodes
the PIL mode to `RGB` for 3-sample frames and `L` otherwise
(python-sane sane.py:303) - so even a truthful backend transferring
packed 1-bit wire data (hpaio Lineart reports depth 1) arrives as
8-bit grayscale. hpaio also exposes no `depth` option, so a 1-bit
request on that device can only be expressed through a bilevel `mode`
value. Both facts favour keying the check on the delivered image mode
rather than SANE parameters, and make the bilevel-mode matching
essential rather than optional.

## Goals / Non-Goals

**Goals:**

- A requested 1-bit depth becomes a contract: imported pages are 1-bit
  even when the backend reneges.
- One conversion implementation, one user-facing knob (the existing
  "threshold tool" value), shared with Tools → Threshold and
  "Threshold before OCR".

**Non-Goals:**

- Predicting backend behaviour before scanning (e.g. flagging the
  depth=1 + compression=jpeg combination in the dialog); detection is
  post-snap only, keyed on the delivered frame.
- Changing the threshold tool itself or decoupling "Threshold before
  OCR" from OCR.
- Any conversion when 1-bit depth was not requested.
- Save-time heuristics on grayscale pages.

## Decisions

### Detect at the scan dialog boundary, keyed on the delivered image mode

`new_page_callback` (dialog/sane.py:546) has both the delivered image
and `self.current_scan_options`. It determines whether the scan
requested 1-bit output - the profile's `depth` option set to 1, or a
`mode` option value naming a bilevel mode - and compares that with the
image mode: requested bilevel and mode != "1" is a mismatch. The
mismatch is passed to `_new_scan_callback` as a new "new-scan" signal
argument and mapped to an import option.

The bilevel mode-value list comes from the installed SANE backend
documentation, not guesswork: "Lineart"/"Line art"/"LineArt" (epsonds,
fujitsu, genesys, pixma, ...), "Binary" ("black and white only (1
bit)"), "Black & White", and the 1-bit dithered modes "Halftone" and
"Error Diffusion". The match is against the whole value, so a
hypothetical "ColorLineart" cannot pass. Deliberately excluded:
"monochrome" and "linear" never appear as mode values in backend
documentation and read as grayscale or film modes, and "Text Enhanced"
appears only in prose. An unknown mode value, or no mode option at
all, means no conversion is attempted (the safe default).

- Alternative: read the depth from `get_parameters()` in
  `do_scan_page` and plumb it through the worker-thread response.
  Rejected: more plumbing across the thread boundary for the same
  result; the snapped image's mode is equally authoritative.
- Alternative: detect in `_new_scan_callback` by reaching into the
  scan dialog's profile from the window mixin. Rejected: the dialog
  already owns the profile; the signal payload is the established
  channel for scan facts (resolution travels the same way).
- Alternative: substring matching for mode values. Rejected: risks
  false positives like "ColorLineart"; full-value matching keeps the
  predicate conservative.

### Convert in the worker as the first post-process step

The import option (e.g. `"enforce_depth": True`) is handled in
`_post_process_scan` before rotate, unpaper, UDT and OCR by calling
the existing `threshold` handler with the configured
"threshold tool" value. Conversion of a large frame must not run on
the GUI thread; the post-process chain already threads these steps and
reports progress. Running first also means later steps see a stable
1-bit page, and an OCR threshold pass afterwards is a harmless no-op
on already-1-bit data.

- Alternative: binarize inside `new_page_callback` on the GUI thread.
  Rejected: an A4 600 dpi colour frame makes the UI jank visible.
- Alternative: convert in the SANE worker immediately after `snap()`.
  Rejected: mixes acquisition with policy on the frontend thread and
  the profile is not consulted there.

### Reuse `do_threshold`, not `_to_bilevel`

The colour-aware min-channel semantics keep coloured marks (yellow
text, red stamps) as ink on white paper, matching the documented
`page-threshold` behaviour and the user's mental model of the existing
tool. `_to_bilevel`'s fixed 40% luminance cutoff is a different,
lesser semantic reserved for save-time codec coercion.

### Non-blocking notification

The mismatch is always logged (`logger.warning`) and surfaced once per
batch through the existing scan progress messaging, never as a modal
dialog: a 50-page ADF batch with a misbehaving backend must not
produce 50 popups. The progress channel is already lifecycle-managed
and cancellable.

## Risks / Trade-offs

- [Binarization is destructive: a user who set depth=1 but actually
  wanted the 8-bit hardware-JPEG data loses it] → The application only
  converts when the user explicitly requested 1-bit, informs the user
  when it does, and Undo restores the pre-conversion page.
- [Profiles may store the depth under a synonym option name] → The
  lookup follows the same option-name matching the scan dialog uses to
  set profile values; if no depth option is found, no conversion is
  attempted (the safe default).
- [Two "threshold" pathways now coexist (depth enforcement and
  threshold-before-OCR)] → Both call the same handler with the same
  value; no new semantics are introduced. Decoupling the OCR coupling
  stays out of scope.

## Migration Plan

Single-commit change; no configuration or data migration. Rollback is
reverting the signal arity and the post-process step.

## Open Questions

(none)
