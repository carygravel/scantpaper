## Context

The save path carries the JPEG quality from the dialog to the encoder as a
`float`. The `jpeg_quality` GObject property is `type=float`
(`dialog/save.py`), populated from a `Gtk.SpinButton.get_value()`, and
stored into `settings["quality"]`. At the encoder (`page.py:_encode_jpeg`)
the value is handed straight to `PIL.Image.save(..., quality=...)`. Pillow
>= 12 rejects non-integer qualities with `ValueError: Invalid quality
setting`, so JPEG and JBIG2 (which resolves to the JPEG branch) saves fail.

See proposal.md - Why for the motivating failure.

## Goals / Non-Goals

**Goals:**
- Guarantee the quality passed to Pillow's JPEG encoder is always a valid
  integer in range, so lossy saves never fail on a float-typed value.
- Make the source of truth in the save dialog an integer-typed property.
- Add regression coverage for the float-quality case.

**Non-Goals:**
- Changing the quality UI (range, label, visibility rules).
- Altering the codec-selection behaviour for any compression option.
- Touching JPEG 2000's quality handling beyond what the shared float fix
  implies.

## Decisions

### Normalise quality to an integer at the encoder

`_encode_jpeg` SHALL coerce its `quality` argument to `int` (via
`round()` to honour the fractional intent) before calling Pillow. This is
the single choke point every lossy caller funnels through (`page.py:549`
and the shared JPEG branch used by JBIG2), so one change protects all
paths, including any future caller.

- Alternative considered: coercing at the call site in
  `write_image_for_pdf`. Rejected: it leaves `_encode_jpeg` still able to
  receive a float from another caller and scatters the invariant.
- Rationale for `round()` over truncation (`int()`): a quality of `75.9`
  truncating to `75` is acceptable, but rounding preserves the user's
  intent for values above `x.5`; the range clamp in Pillow remains the
  backstop.

### Type the quality property as an integer

`jpeg_quality` SHALL become `type=int` (range unchanged at 1–100). The
value read back from the spinbutton is still a float, so the assignment in
`file_menu_mixins.py` and the spinbutton round-trip must convert to `int`
at read time. This removes the float at its origin and keeps the stored
`settings["quality"]` an integer for all image types (PDF, TIFF, JPG).

- Alternative considered: leaving the property a float and relying solely
  on the encoder coercion. Rejected: the property is the canonical source,
  and typing it `int` makes the whole chain correct rather than patching
  only the last hop.
- Note: the existing JPEG 2000 encoder already produces an integer via
  `round(...)` internally, so it is unaffected; the encoder coercion keeps
  it consistent.

## Risks / Trade-offs

- [JPEG 2000 `quality_layers` / rate uses the same `quality` value] →
  The coercion happens in `_encode_jpeg` only; `_encode_jp2` keeps its own
  `round` and is not regressed.
- [A config file could hold a non-numeric or out-of-range `quality`] →
  `config.DEFAULTS` and the dialog range constrain values; the encoder
  coercion plus Pillow's own validation remain as backstops. Out-of-scope
  for this change.
- [Rounding changes an existing integer-valued float (e.g. `75.0`) to the
  same integer `75`] → No observable behaviour change for the common case.

## Migration Plan

No data migration required. `settings["quality"]` is re-derived from the
dialog on every save, so existing config files are unaffected.

## Open Questions

None.
