## Context

See `proposal.md` for the motivation and `specs/ocr-recognition/spec.md` for
the required behaviour.

The current OCR path already carries a free-form language string:

- `OCRControls` builds a single-select `ComboBoxText` from the installed
  tesseract codes and stores the selected code.
- The scan dialog and the OCR tools dialog persist that code in the existing
  `"ocr language"` setting.
- `Document.ocr_pages` forwards it to `DocThread.do_tesseract`, which passes
  it to `PyTessBaseAPI(lang=...)`.

Tesseract itself accepts `deu+eng`, so the backend needs no change for
multi-language recognition. The UI and the engine initialisation are the
gaps.

Two platform constraints shape the design:

- The application must keep OCR in memory. The OCR speed change
  (`openspec/changes/archive/2026-08-16-ocr-speed/`) removed temporary PNG and
  hOCR files; a subprocess or CLI-argument design would undo that.
- The minimum tesserocr versions in supported distributions are 2.5.2
  (Jammy) and 2.6.0 (Noble). The `variables=` constructor argument only exists
  from 2.7.0, so the implementation must use `PyTessBaseAPI(init=False)`
  followed by `InitFull(path=..., lang=..., variables=...)`, which is available
  in both.

## Goals / Non-Goals

**Goals:**

- Let users select several OCR languages with a clear primary language.
- Let users pass additional tesseract engine variables, including a user word
  or pattern list, without adding a shell or CLI parser.
- Keep existing configuration and single-language behaviour working.
- Detect invalid options before any page is modified.

**Non-Goals:**

- Raw command-line argument parsing, including shell quoting and `--flag`
  syntax.
- First-class page-segmentation (PSM) or OCR-engine-mode (OEM) controls.
  `tessedit_pageseg_mode` is overwritten by engine initialisation, and
  `tessedit_ocr_engine_mode` is unreliable as a variable, so these need API
  arguments of their own in a later change.
- A tessdata directory picker. The documented workaround is
  `TESSDATA_PREFIX` or replacing the system models.
- Changing the locale-aware default language. When no language is stored, the
  existing first-installed fallback is kept.
- Any change to the in-memory OCR pipeline or to the stored page image.

## Decisions

### Store the language selection as a `+`-joined string

Reuse the existing `"ocr language"` setting and store the primary language
first, followed by the additional languages in selection order, for example
`deu+eng+fra`.

- Why: this is exactly the format tesserocr and tesseract already accept, it
  needs no configuration migration, and existing single-language values remain
  valid.
- Alternative: store a JSON list. It would make the UI state explicit, but it
  would require a migration and would not match the engine API.

The string is parsed and composed by helpers in `tesseract.py`
(`split_language_spec`, `join_language_spec`) so the UI, validation, and tests
share one implementation.

### Use a primary combo plus an additional-languages popover

`OCRControls` keeps the existing combo as the primary-language selector. A new
`Gtk.MenuButton` labelled with the selected additional languages opens a
`Gtk.Popover` containing a scrolled `Gtk.ListBox` of `Gtk.CheckButton` rows, one
per installed language other than the primary. The button label shows the
chosen additional languages in selection order, or a "None" label when empty.

- Why: it keeps the primary language obvious, avoids a second always-visible
  list, and uses standard GTK4 widgets available in GTK 4.6.
- Why not a single editable field: it would force users to know tesseract
  codes and the `+` syntax.
- Why not a multi-select list in the dialog: it is taller and makes the
  primary/additional distinction less clear.
- Selection order is maintained in a list: checking a language appends it,
  unchecking removes it. Changing the primary removes it from the additional
  list and rebuilds the rows. `language` remains the canonical `+`-joined
  string; a recomputation guard prevents signal loops while the UI is rebuilt.

Missing languages are not silently replaced. The primary combo includes a
stored-but-missing code as a row labelled `(not installed)`, and the popover
includes missing additional codes as checked rows with the same label. This
lets the user see and remove them while validation refuses to start OCR.

### Put the language and options controls in one sensitivity container

The current language row is the only child toggled by the OCR active
checkbox. Add a vertical container that holds the language row, the
additional-languages row, and the advanced expander, and toggle that container
instead. This keeps the new controls disabled when OCR is off and gives tests
one stable widget to inspect.

### Accept `name=value` engine variables, not CLI arguments

Add an `Advanced Tesseract options` expander containing a short instruction
label and a multi-line `Gtk.TextView` in a `Gtk.ScrolledWindow`. One entry per
line:

```
user_words_file=/home/me/words.txt
tessedit_char_whitelist=0123456789
```

Parsing rules:

- Blank lines are ignored.
- A line whose first non-whitespace character is `#` is a comment and is
  ignored.
- A name is the text before the first `=`; the value is the rest of the line
  with surrounding whitespace removed. Values may contain further `=` signs.
- Duplicate names: the last value wins, matching a dictionary.
- No shell quoting, variable expansion, or `~` expansion is performed. Paths
  should be absolute. This is documented in the field tooltip and README.

The raw text is stored in a new `"tesseract variables"` setting, default `""`,
so comments and ordering survive a restart. It is parsed each time OCR runs;
the parser is cheap and keeping raw text avoids a second serialisation format.

### Apply variables during engine initialisation

`do_tesseract` changes from:

```python
with tesserocr.PyTessBaseAPI(lang=options["language"], path=path) as api:
```

to:

```python
with tesserocr.PyTessBaseAPI(init=False) as api:
    api.InitFull(path=path, lang=options["language"], variables=variables)
    ...
```

`InitFull` is the only cross-version way to pass init-only variables such as
`user_words_file`. `SetVariable` is not usable for these because calling it
before `Init` reverts to the defaults. The hOCR runtime variables
(`tessedit_create_hocr`, `hocr_font_info`) are still set with `SetVariable`
after initialisation, as they are runtime settings.

`InitFull` silently ignores unknown variable names. As a safety net after
initialisation, each supplied name is checked with
`api.GetVariableAsString(name)`: an unknown name returns `None`. If that
happens, the worker raises an error naming the variable before the page is
modified. The UI normally catches this earlier, so the fallback should not be
seen in normal use.

### Validate before dispatch, with a worker fallback

A shared `OCRControls.validation_error` returns `None` or a user-facing
message. It checks:

1. A language is selected.
2. Every code in the language specification is installed.
3. The advanced text parses.
4. Every variable name is recognised by tesseract.

For step 4, add a cached `get_tesseract_variables()` helper in `tesseract.py`
that runs `tesseract --print-parameters` and parses the first token of each
parameter line. This reuses the existing CLI dependency (`--list-langs`) and
avoids initialising an engine on the GTK main thread. If the command fails or
its output cannot be parsed, validation fails open (the names are not checked)
so a tesseract quirk does not block OCR.

Flow behaviour:

- The OCR tools dialog validates when the user presses OK. On error it shows
  the existing message dialog and does not dispatch OCR.
- The scan dialog validates when the user presses Scan. On error it shows the
  message dialog and sets a transient per-batch flag. `_new_scan` checks the
  flag and omits OCR for that batch, so the scan can still proceed and no page
  is modified. The persistent `OCR on scan` setting is not changed. The flag is
  reset on the next Scan click.

### Pass the variables through the existing option dictionaries

The scan callback and the tools flow add the `"variables"` option, taken from
`settings["tesseract variables"]`. `Document._post_process_ocr` forwards it to
`ocr_pages`, and
`do_tesseract` reads it with `options.get("variables", "")`. This mirrors how
`language` is already carried and avoids changing the worker protocol.

### Default language behaviour is unchanged

If no language is stored, the first installed code is still selected, as
today. A locale-aware default is a separate user-visible change and is left
out of this proposal.

## Risks / Trade-offs

- **tesserocr version drift** → Use only the `init=False` + `InitFull` path,
  which exists in 2.5.2 and later. Add a mocked unit test asserting the
  initialisation arguments and keep the real integration test runnable on a
  system with only one language.
- **`tesseract --print-parameters` output changes** → Parse only the first
  whitespace-delimited token and fail open if the command or format is
  unexpected. The worker check remains as a safety net.
- **Advanced variables can make OCR fail or crash** → Validate syntax and
  names, report errors before dispatch, and document that the field accepts
  tesseract engine variables rather than arbitrary CLI flags.
- **More languages can be slower and less accurate** → Document that only the
  needed languages should be selected and that the main language belongs
  first.
- **Missing-language handling changes existing behaviour** → Previously a
  missing code was silently replaced. The new UI shows `(not installed)` and
  blocks OCR instead. This is a bug fix, but it is user-visible and needs a
  README/release note.
- **New UI strings add translation work** → Keep labels short, put examples in
  the README, and mark new PO entries fuzzy for translator review.
- **The popover adds GTK code** → Use only standard GTK 4.6 widgets and cover
  the selection logic with widget-level tests, not screenshot tests.

## Migration Plan

- Add `"tesseract variables": ""` to `DEFAULTS`; configuration files without
  the key load unchanged.
- No database schema change and no migration of `"ocr language"`.
- Rolling back is safe: the old UI ignores the new setting, and existing
  single-language values continue to work.

## Open Questions

- Should the default language follow the system locale instead of the first
  installed code? Deferred to a separate change.
- Should the advanced field gain file-chooser buttons for
  `user_words_file`/`user_patterns_file`? Deferred; the text field covers the
  requested use case.
- Should a later change add first-class PSM/OEM selectors and a tessdata
  directory picker? Deferred; they need API arguments rather than variables.
