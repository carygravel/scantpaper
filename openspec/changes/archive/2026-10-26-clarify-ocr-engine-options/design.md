# Design

## Context

See `proposal.md` - Why. The current state that shapes the approach:

- `scantpaper.tesseract.parse_variables` splits one `name=value` per line and
  rejects a line without `=`.
- `OCRControls.validation_error` (`postprocess_controls.py`) parses the field,
  checks the language, and checks every name against
  `get_tesseract_variables()`, which parses `tesseract --print-parameters`.
- `DocThread.do_tesseract` calls `api.InitFull(path, lang, variables)` and
  raises when `GetVariableAsString(name) is None`.
- At import, tesserocr runs `SetVariable("debug_file", "/dev/null")`, so
  tesseract's own warnings are discarded. A missing `user_words_file`
  therefore reports nothing anywhere, which is the silent no-op this change
  removes. Verified on tesseract 5.5.0 / tesserocr 2.11.0: redirecting
  `debug_file` to a real file reveals `Error: failed to load <path>` at
  engine init.

## Goals / Non-Goals

**Goals:**

- Make the accepted syntax obvious without reading the source, and make the
  error for a pasted CLI flag actionable.
- Turn a file-valued parameter that cannot be loaded from a silent no-op into
  a reported error before any page is modified.
- Keep the parsing and validation logic shared by the scan dialog and the
  Tools -> OCR dialog.

**Non-Goals:**

- A general command-line parser or shell semantics (quoting, `%` expansion).
  Flags are only recognised well enough to explain themselves.
- Page segmentation / engine mode controls, and a tessdata directory picker
  (separate change `add-ocr-psm-oem-controls`).
- Expanding `~` or environment variables in paths.

## Decisions

### Recognise a flag by prefix; do not parse the command line

A non-ignored line whose first non-whitespace characters are `-` or `--` is a
command-line option, not an engine parameter. A small module-level mapping in
`tesseract.py` names the equivalent parameter for the flags that have one and
is reused by the error message and the README:

```
--user-words    -> user_words_file
--user-patterns -> user_patterns_file
--dpi           -> user_defined_dpi
```

- Why: the message the user needs is "this is a flag; here is the parameter".
  A general parser would silently accept one CLI dialect while still failing
  on `-l`, `--tessdata-dir` and friends, which invites more confusion.
- Alternative: accept the mapped flags and translate them. Rejected - it
  teaches a dialect the field does not actually implement and makes
  `--tessdata-dir` look like an oversight rather than a boundary.

### Accept the `-c` prefix as the same syntax

`-c name=value` is the command-line spelling of an engine parameter, so the
parser strips a leading `-c` token before parsing `name=value`. This is safe
because parameter names never start with `-`.

### Treat the file check as a hard error, before dispatch

`user_words_file` and `user_patterns_file` are resolved with `Path.resolve()`
and checked for existence and readability. A failure is reported by
`validation_error` and no OCR is dispatched, matching the existing rule that
invalid options are rejected before any page is modified. The resolved
absolute path is reported so a relative path or unexpected working directory
is visible. The resolved path is also the value passed to the engine, so the
check and the engine cannot disagree.

- Why error rather than warning: running OCR without the configured word list
  silently produces a different result from what the user asked for, which is
  the confusion this change exists to remove.
- Alternative: warn and continue. Rejected for the same reason.
- The check lives in `validation_error` so both dialogs share it; the worker's
  existing unknown-name check stays as a safety net for non-GUI callers.

### Record the applied options in the worker log

`do_tesseract` already logs the parsed variables at INFO. Extend that line to
the resolved file paths so a user running with `--log` can confirm what was
applied. This is the only feedback channel for "is it actually used?", since
tesseract's own messages are suppressed.

### Put the flag guidance in the field, not only the tooltip

The field label, the hint under the text view, and the README all state that
the field takes `name=value` engine parameters, that `-c` is optional, and
that `--flags` belong on the tesseract command line. New strings are marked
`#, fuzzy` in the PO catalogs per `AGENTS.md`.

## Risks / Trade-offs

- A user who has a bad path today sees no error and OCR "works"; after this
  change OCR is blocked until the path is fixed - intended, and mitigated by
  reporting the resolved path in the message.
- Relative paths: resolving to absolute keeps behaviour equivalent (same
  process working directory) while making the reported path truthful.
- The flag mapping can go stale as tesseract adds options; it is deliberately
  small, covered by tests, and an unrecognised flag is still rejected as a
  flag without a suggested parameter.
- If `tesseract --print-parameters` fails, name validation already fails open;
  the file check and flag check are independent of it.
- `~` is not expanded, so `~/words.txt` now fails with a clear message instead
  of being passed to the engine and ignored.

## Open Questions

- Expand `~` and environment variables in file-valued parameters? Deferred;
  it is a separate behaviour and needs a decision on precedence.
- Add a "Test options" action that initialises the engine once and reports
  success? Deferred; it duplicates engine start-up.
- Reject the other parameters the application sets itself
  (`tessedit_create_hocr`, `hocr_font_info`)? Deferred; they are not plausible
  user settings and rejecting them is a separate cleanup.
