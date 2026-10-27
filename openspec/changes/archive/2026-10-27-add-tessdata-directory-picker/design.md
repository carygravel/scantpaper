# Design

## Context

See `proposal.md` - Why for the motivation. Two current facts shape the
approach:

- `OCRControls` builds its language list once, in
  `_add_tess_language_controls()`, from `get_tesseract_codes()` and never
  refreshes it. The Tools -> OCR dialog and the scan dialog are each created
  once and reused, so a directory change made anywhere else would leave both
  with a stale list.
- The data directory is an engine initialisation argument. `InitFull()`
  takes `path=`, while `-c` variables cannot change it; `m_data_sub_dir` is a
  removed Tesseract 3 parameter and stays rejected.

The worker currently calls `tesserocr.get_languages()` without arguments and
falls back to `_find_tessdata_path()` in `docthread.py` when Tesseract reports
`./`. The fallback knows about distribution layouts that the picker does not
need to duplicate, so it is shared rather than reimplemented.

A `TESSDATA_PREFIX` naming a broad parent such as `/usr/share` makes both
`tesserocr.get_languages()` and `tesseract --list-langs` recurse until they
are killed. The language list is built while the dialog opens, before the user
can act, so the guard has to run before either call.

## Goals / Non-Goals

**Goals:**

- One resolver used by the OCR dialog, the worker, and the startup locale
  check, so the list of languages and the engine cannot disagree.
- The dialog must never block on a broad `TESSDATA_PREFIX`.
- A directory change must take effect in the already-created dialogs.

**Non-Goals:**

- Discovering candidate directories. The picker offers a path entry, a folder
  chooser, and a reset; it does not guess.
- Custom search roots or recent-directory history.
- Changing engine-mode compatibility or accepting `m_data_sub_dir` /
  `--tessdata-dir` in the advanced field.

## Decisions

### The picker lives in `OCRControls`

`OCRControls` is the only component shared by both OCR entry points, and it
owns the language list that the directory controls. Putting the row there
means `on_tessdata_dir_changed` can rebuild the list immediately; no signal
from Preferences to every dialog is needed.

Alternative: a Preferences setting next to `TMPDIR`. Rejected because the
dialogs are created once; they would show languages from the old directory
until reopened, and the user would have no feedback in the place where the
mistake happens.

Alternative: both a global default and per-dialog override. Rejected as two
storage paths and two failure modes for one value.

### A store-and-display entry, not a detected combo

The row is a `Gtk.Entry` with a `Browse...` folder chooser and a `Default`
button, mirroring the temporary-directory preference. The entry placeholder
is `Default (system tessdata)`. Empty means automatic.

Alternative: a combo of discovered directories. Rejected: it needs
heuristics (siblings, `TESSDATA_PREFIX`, home locations), surfaces "why isn't
my directory listed?", and still needs Browse. Discovery can be a later,
separate change if users ask for it.

### Resolution precedence and the direct-`.traineddata` rule

`tesseract.py` gains:

```text
validate_tessdata_dir(path) -> error message | None
resolve_tessdata_dir(explicit) -> (path with trailing separator, error)
find_system_tessdata_dir() -> path | None      # moved _find_tessdata_path
get_tesseract_codes(path=None) -> list[str]
```

`resolve_tessdata_dir()` follows one order:

1. Non-empty explicit selection. Expand `~`, normalise, validate.
2. `TESSDATA_PREFIX`, if set. Validate before any Tesseract call.
3. System default: `tesserocr.get_languages()`, then
   `find_system_tessdata_dir()` when it reports `./`. Validate.

The validation rule is: exists, is a directory, is readable, and directly
contains at least one `*.traineddata`. "Directly" is what makes the guard
work; a recursive check would accept `/usr/share` again.

An error from step 1 or 2 is returned, not swallowed. The caller reports it
and OCR does not start. There is no fallback to the next source, which would
make a typo silently select different models.

`get_tesseract_codes(path)` passes `--tessdata-dir <path>` to
`tesseract --list-langs` when a path is known, so the list matches the
directory that will be used. This keeps the existing subprocess-based
discovery rather than switching to `tesserocr.get_languages(path)`; either
works, and the subprocess path already handles the `List of available
languages` header.

Alternatives: rely on `TESSDATA_PREFIX` alone (rejected - not inherited by
desktop launches); accept any directory and let Tesseract fail (rejected -
the failure mode is a hang or a silent default).

### The dialog resolves before building the language list

`_add_tess_language_controls()`:

1. Calls `resolve_tessdata_dir(self._tessdata_dir)`.
2. On error, stores the message in `self._tessdata_dir_error`, uses an empty
   language list, and does not call Tesseract.
3. Otherwise stores the resolved path and builds the list from it.

`validation_error` reports a stored directory error before the language
checks. This means opening the dialog with a broad `TESSDATA_PREFIX` shows an
error instead of freezing.

When the entry changes (`activate` or focus-out) or Browse returns a folder,
the dialog resolves and rebuilds the list. The current primary and additional
languages are kept in `_primary_language` / `_additional_languages`;
`_language_label()` already appends "(not installed)" for codes missing from
`_tesscodes`, and `validation_error` already rejects missing languages, so
the existing behaviour is reused rather than duplicated.

An empty entry plus an invalid `TESSDATA_PREFIX` is an error, not a request
to ignore the environment: the user asked for "automatic", and automatic
means the environment when it is set.

### The worker resolves again and passes `path=`

The dialog passes its setting as `tessdata_dir` with the other OCR options.
`do_tesseract()` calls `resolve_tessdata_dir(options.get("tessdata_dir", ""))`
instead of `tesserocr.get_languages()` plus a local fallback. On error it
sends the message through `request.error()` and returns without touching the
page. On success it passes the returned path to `InitFull(path=...)`;
`InitFull` requires a trailing separator, which the resolver supplies.

The worker does not trust the dialog: a directory can be removed or
unmounted between validation and OCR, and the same resolver also guards
calls that bypass the dialog.

### Persistence matches the other OCR options

`config.py` gains `"tessdata directory": ""`. `ToolsMenuMixins` and
`ScanMenuItemMixins` pass `settings.get("tessdata directory", "")` into
`OCRControls` and write `ocr_controls.tessdata_dir` back on OK, alongside
`ocr language`, `ocr psm`, and the rest. Configurations without the key load
unchanged because of the default.

The scan dialog also uses `OCRControls`; storing there keeps the two entry
points consistent without a second settings path.

### Startup locale check uses the same guard

`app_window.py` passes `get_tesseract_codes()` to `locale_installed()`.
`get_tesseract_codes()` without a path resolves the directory first. If the
environment is invalid it returns an empty list rather than hanging. The
missing tesseract-language warning may then be skipped; the invalid
environment is logged. Blocking startup or raising a modal dialog there
would be disproportionate, and OCR itself is already guarded when the user
opens the dialog.

## Risks / Trade-offs

- **A wrong directory is chosen and OCR runs against it** -> The language
  list comes from the same directory and `validation_error` rejects languages
  not installed there, so the mistake is visible before dispatch. The log
  records the resolved path.
- **The directory disappears after validation** -> `InitFull` fails and the
  existing "Failed to initialise OCR" error names the engine mode; the worker
  re-validates first and reports the directory instead when it is gone.
- **Broad `TESSDATA_PREFIX` blocks OCR until fixed** -> Intended: the
  alternative is a hang. The error names the expected direct directory, and
  an explicit selection overrides the environment.
- **Rebuilding the list loses a selection** -> Selections are stored in the
  control's own state and re-rendered, not read back from the widgets, so a
  missing language survives as "(not installed)".
- **Two code paths could drift** -> Only `resolve_tessdata_dir()` knows the
  precedence and validation; UI, worker, and startup call it.

## Migration Plan

No data migration. The new setting defaults to `""`, so existing
configurations keep the automatic behaviour. Rollback is removing the
setting; an unknown key in an older build is ignored by the existing
settings loader.

## Open Questions

None.
