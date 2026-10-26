# Design

## Context

See `proposal.md` - Why. The current state that shapes the approach:

- `DocThread.do_tesseract` uses `tesserocr.PyTessBaseAPI(init=False)` and
  `api.InitFull(path=..., lang=..., variables=...)`, then sets the hOCR
  runtime variables with `SetVariable`.
- The supported tesserocr versions are 2.5.2 (Jammy) and 2.6.0 (Noble); their
  `InitFull` takes an `oem` argument but has no `psm` argument. `psm=` was
  added later and would raise `TypeError` on those versions.
- tesserocr's `InitFull` applies its page segmentation mode with
  `SetPageSegMode(psm)` after the engine is initialised, so a
  `tessedit_pageseg_mode` supplied as an init variable is overwritten. Verified
  on tesseract 5.5.0: after `tessedit_pageseg_mode=6`, `GetPageSegMode()`
  still returns the automatic mode.
- `tessedit_ocr_engine_mode` is passed through to the engine, but requesting a
  mode the traineddata does not provide makes initialisation fail, which
  tesserocr reports as `Failed to init API, possibly an invalid tessdata
  path: ...` - a misleading message.

## Goals / Non-Goals

**Goals:**

- Let the user choose a page segmentation mode and an engine mode that take
  effect.
- Remove the two silent-ignore paths: a value that is accepted must apply, or
  it must be rejected with a message that explains why.
- Keep the current defaults so nothing changes for a user who does not touch
  the new controls.

**Non-Goals:**

- A tessdata directory picker or `TESSDATA_PREFIX` handling.
- Per-page or per-document-type segmentation presets.
- Turning the advanced field into a command-line parser; that belongs to
  `clarify-ocr-engine-options`.

## Decisions

### Apply the page segmentation mode after initialisation

Call `api.InitFull(...)` and then `api.SetPageSegMode(psm)`.

- Why: it is the only spelling that works in 2.5.2, 2.6.0 and 2.11 alike, and
  it is the same call that currently overwrites `tessedit_pageseg_mode`, so
  the control wins for the same reason the variable loses.
- Alternative: pass `psm=` to `InitFull`. Rejected - it breaks the minimum
  supported tesserocr versions.

### Apply the engine mode through the `oem` argument

Map the stored setting to `tesserocr.OEM` and pass it as `InitFull(oem=...)`,
defaulting to `OEM.DEFAULT` (today's behaviour).

- Why: `oem` exists in every supported version and is the parameter the engine
  expects at initialisation, unlike `tessedit_ocr_engine_mode`.
- Availability cannot be probed cheaply per language, so all four modes are
  offered. When initialisation fails, the worker catches it and raises an
  error naming the engine mode instead of tesserocr's "invalid tessdata path".
  The failure happens before `Recognize`, so no page is modified.

### Curated page segmentation list, numeric storage

Offer the modes from `tesseract --help-psm` that are meaningful for scanned
pages (automatic, single column, single block, single line, single word,
single character, sparse text, raw line), labelled with tesseract's names.
Store the numeric value; an empty or unrecognised stored value means the
automatic mode. Automatic is the default, matching today.

- Why numeric: it is what the API takes and what `--psm` means; the label is
  presentation only.

### Persist two new settings, defaulting to current behaviour

Add `"ocr psm"` (empty = automatic) and `"ocr engine mode"` (`"default"`) to
`config.py` `DEFAULTS`. Existing configuration files load unchanged, and an
older release ignores the keys, so rollback is safe.

### Reject the parameter names the controls own

`validation_error` rejects `tessedit_pageseg_mode` and
`tessedit_ocr_engine_mode` with a message pointing at the new controls.

- Why: accepting them is exactly the silent no-op being fixed; letting the
  control silently override a typed value is the same bug with extra steps.
- Alternative: keep accepting them and let the control win. Rejected.

### UI as combo rows in the existing options container

Use the same `ComboBoxText` pattern as the language selector and place both
rows in the container that the OCR active toggle already disables, so
sensitivity handling needs no new mechanism.

## Risks / Trade-offs

- A user who relied on `tessedit_pageseg_mode=6` today gets an error and must
  use the control - intended, and the error says so.
- Choosing a legacy engine mode on data without a legacy engine blocks OCR
  until changed; the error names the mode, which is better than "invalid
  tessdata path" but still blocks. The control could later be filtered to the
  modes the data offers.
- Two new configuration keys and new translatable strings; PO entries are
  marked `#, fuzzy`.
- Segmentation semantics are engine-specific and hard to unit test with the
  real engine; unit tests assert the `InitFull(oem=...)` and
  `SetPageSegMode(...)` calls against a fake API, with one real-engine test
  kept for the default path.

## Migration Plan

- Defaults keep the automatic mode and the default engine mode, so behaviour
  is unchanged for existing users.
- No database schema change; the settings live in the user configuration like
  the other OCR options.
- Rollback: the older release ignores the two new keys and reads
  `tessedit_pageseg_mode`/`tessedit_ocr_engine_mode` from the advanced field
  again.

## Open Questions

- Per-page segmentation overrides for mixed documents? Deferred; the setting
  is global like the language.
- Show each mode's description next to the combo? Deferred; keep the control
  short and rely on the tesseract names and the README.
