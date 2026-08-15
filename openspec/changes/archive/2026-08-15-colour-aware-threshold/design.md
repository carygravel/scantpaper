## Context

The threshold tool's transform lives in `do_threshold()` (docthread.py): it
converts the page to greyscale (`convert("L")`), applies a point threshold, and
converts to 1-bit. Two facts shape this design:

1. The luma conversion discards colour, so coloured content whose luminance
   approaches white (yellow text, pink/light-blue marks) is erased.
2. The slider is `0..100` but is compared **raw** against `0..255` pixel values
   (`lambda p: 255 if p > options["threshold"] else 0`), so the default of 80
   means "black when grey ≤ 80/255 (~31%)", not 80%. The predecessor tool used
   ImageMagick's `-threshold`, which takes a percent; the rewrite to Pillow
   appears to have dropped the `/2.55` scaling. We treat this as a bug: the new
   slider is a true percent and the old raw-comparison behaviour is not
   reproduced.

The setting `threshold tool` (default 80) is shared by the threshold dialog
(tools_menu_mixins.py), the OCR threshold spinbutton (postprocess_controls.py),
and an OCR path that currently passes the value to `do_tesseract` unused.

See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**
- Colour-aware binarisation: a pixel is ink when it differs from white in any
  single channel by more than the threshold — not when its luminance is low.
- Make the slider a true percentage of the full range (0–100 → 0–255).
- New default of 20.
- One-time migration of saved `threshold tool` values so existing greyscale
  documents threshold identically after the upgrade.
- No new dependencies (pure Pillow).

**Non-Goals:**
- Automatic detection of non-white paper backgrounds (coloured paper, yellowed
  pages) — future extension.
- Otsu / adaptive (Sauvola) thresholding — future extensions.
- Fixing the inert "threshold before OCR" pass-through to `do_tesseract`.
- Changing the 1-bit output mode.

## Decisions

### 1. Transform: ink strength = distance from white

A pixel is ink when `255 − min(R, G, B) > t · 2.55`, i.e. black when
`min(R, G, B) < cutoff` where `cutoff = round(255 · (100 − t) / 100)`.

```
current:  grey = 0.299R + 0.587G + 0.114B     → black iff grey ≤ v
proposed: min  = min(R, G, B)                  → black iff min < cutoff
```

Any colour that differs strongly from white in a single channel is kept. For a
greyscale pixel, `min(R,G,B)` equals the grey value, so the transform is a
strict generalisation of the old luminance threshold.

Implementation (Pillow only — `point()` on an RGB image maps each band
independently, so the minimum must be computed first):

```python
from PIL import ImageChops

cutoff = round(255 * (100 - threshold) / 100)
image = page.image_object.convert("RGB")
red, green, blue = image.split()
min_channel = ImageChops.darker(ImageChops.darker(red, green), blue)
page.image_object = min_channel.point(lambda p: 0 if p < cutoff else 255).convert("1")
```

Alternatives considered:
- **Keep luma but raise Otsu** — fixes slider tuning, still cannot separate
  equal-luminance colours. Rejected.
- **Euclidean distance to white** — no benefit over `max`-channel deviation for
  a white background, more per-channel work. Rejected.
- **numpy** — makes the transform trivial but adds a declared dependency for no
  functional gain. Rejected.

### 2. Slider semantics become a true percent; default 20

The threshold dialogs relabel the slider as an ink-strength cutoff: "higher =
only stronger marks kept". The default in `config.py` (`threshold tool`) and
`postprocess_controls.py` (`_threshold_value`) becomes 20. At 20, yellow, red,
crimson, pink, light blue and green annotations are all kept; near-white paper
noise is excluded (cutoff 204).

### 3. One-time config migration for existing saved values

The old slider *intended* percent semantics (the ImageMagick behaviour), so the
sane migration preserves intent rather than the buggy raw output. The new
ink-strength cutoff `t` and the old intended percent `v` are related by
`t = 100 - v`: a greyscale pixel is black when `grey < 2.55(100 - t)`, which is
exactly the "black when grey ≤ 2.55·v" cut-off the user originally intended.
The default maps cleanly (old 80 → 20, the new default). The map is its own
inverse (20 ↔ 80), so it must run exactly once.

The migration runs in `config.read_config()` and is gated so it runs once:
- Trigger only when the config's stored `version` predates this change (the
  version field is written to the config on save via `_pre_flight`); if
  `version` is absent, treat the config as legacy and migrate.
- Existing config tests in test_8_config.py and the migration test in
  test_app_window.py are the pattern to follow.

### 4. Output stays 1-bit

`convert("1")` is kept. The tool remains a binariser.

## Risks / Trade-offs

- [Existing greyscale output changes because the old raw-comparison bug is not
  reproduced] → Intended: the new slider is a true percent, which is what it
  always displayed. The migration maps saved values so the user's intended
  cut-off is kept.
- [Re-running the migration flips the value back (20 → 80)] → The migration is
  gated on the stored config `version` so it runs exactly once.
- [Coloured paper: any background whose `min(R,G,B)` falls below the cutoff is
  treated as ink] → A true cream/white page (min ≈ 240) is safe at the default;
  visibly coloured paper was already broken under the old tool and is flagged
  as a future background-detection extension.
- [Low thresholds keep scanner noise / grey halos] → Expected behaviour; the
  slider lets the user raise the cutoff. Noted in the dialog tooltip.
- [Migration depends on the stored config `version`] → Absent `version` is
  treated as legacy, which is correct for all pre-existing configs.

## Migration Plan

- Config migration is in-place on first run after the upgrade; the rewritten
  value is persisted on the next config save. No separate rollback step —
  the mapped value preserves the cut-off the user intended, so rollback risk
  is minimal.
- Fresh installs get the new default (20) with no migration.

## Open Questions

None blocking. The "threshold before OCR" spinbutton shares the migrated
setting and its relabelled semantics; its value remains unused by
`do_tesseract`, and fixing that is deliberately out of scope.
