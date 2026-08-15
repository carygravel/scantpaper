## Why

The threshold tool converts pages to greyscale (luminance) before binarising,
which erases coloured annotations that are visually distinct from the paper but
similar in luminance. For example, yellow text (luma 226/255) becomes white at
the default threshold, and light-coloured marks such as pink highlighter or
light-blue ink sit right at the cut-off. Any colour whose luminance approaches
white is lost no matter how the slider is set, because the separating
information (hue/saturation) is discarded before thresholding.

## What Changes

- Replace the luminance-based binarisation in the threshold tool with a
  colour-aware "distance from background" transform: a pixel is ink when
  `255 - min(R, G, B)` exceeds the threshold. Any pixel that differs strongly
  from white in any single channel is kept, matching how the eye sees it.
- Invert the threshold slider semantics to "ink strength": the slider now
  expresses how far from the background a pixel must be to count as ink.
  The default becomes 20 (was 80).
- Migrate saved `threshold tool` values to the new scale (map `v -> 100 - v`)
  so the setting keeps the cut-off the user originally intended. The old
  slider was compared raw against 0-255 pixel values despite its 0-100 range
  (a bug carried over from the ImageMagick rewrite); that buggy behaviour is
  not reproduced.
- Keep the output as 1-bit black-and-white, as today.
- Update the affected UI, defaults, and tests.

## Capabilities

### New Capabilities
- `page-threshold`: Applying a threshold to pages to produce a 1-bit
  black-and-white image, preserving visually distinct coloured content.

### Modified Capabilities
<!-- No existing spec describes thresholding behaviour. -->

## Impact

- `scantpaper/docthread.py` — `do_threshold()`: the transform itself (luma
  threshold -> colour-distance threshold).
- `scantpaper/tools_menu_mixins.py` — threshold dialog: relabel the slider and
  its default.
- `scantpaper/config.py` — `threshold tool` default changes from 80 to 20;
  saved-value migration on load.
- `scantpaper/postprocess_controls.py` — `threshold_value` default (OCR
  threshold spinbutton) follows the same semantic inversion.
- `scantpaper/tests/` — tests asserting the old luma semantics or default value
  are updated; new tests cover colour-aware behaviour.
- Note: the same `threshold tool` setting feeds the "threshold before OCR"
  path, which currently passes the value to `do_tesseract` unused (a separate,
  pre-existing no-op). No OCR behaviour is intended to change here.
