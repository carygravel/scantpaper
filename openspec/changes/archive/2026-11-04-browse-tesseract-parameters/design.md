# Design

## Context

See `proposal.md` for motivation; this document records how the pieces fit.

The advanced field is built by `OCRControls._add_advanced_options()`
(`src/scantpaper/postprocess_controls.py`) inside a `Gtk.Expander`, for the
Tesseract branch only. The field is a `Gtk.TextView`, and the `variables`
getter reads its buffer on demand, so writing to the buffer is enough for the
existing settings path to save the value.

The dialog already has the parameter source. `get_tesseract_variables()`
(`src/scantpaper/tesseract.py`) runs `tesseract --print-parameters` once,
caches the name set with `lru_cache`, and returns `None` when the command fails
or the output does not start with the expected header. `validation_error()`
calls it on every OCR confirmation.

Constraints that shape the approach:

- GTK 4.6 is the minimum supported version (README), so `Gtk.ColumnView`
  (4.10+) cannot be used.
- `SimpleList` wraps `Gtk.TreeView` and disables interactive typeahead, as the
  `list-typeahead` spec requires. Its `data` property is bound to the raw
  `Gtk.ListStore`.
- A `Dialog` shown with `run_dialog()` must emit a response on Escape and on
  window close, or the nested main loop never returns. `MultipleMessage`
  overrides both for exactly this reason.

## Goals / Non-Goals

**Goals:**

- One shell-out and one parser shared by validation and the browser.
- Keep the dialog a view: it receives rows and returns a chosen name;
  `OCRControls` writes the field.
- Use only GTK 4.6 primitives and existing project widgets.

**Non-Goals:**

- No retry or refresh when the parameter list could not be read.
- No value editing, completion, or change to validation behavior.
- No persistence beyond the existing field text.

## Decisions

### One cached parser, two views

Add to `tesseract.py`:

```python
@dataclass(frozen=True)
class TesseractParameter:
    name: str
    default: str
    description: str


@lru_cache(maxsize=1)
def get_tesseract_parameters() -> tuple[TesseractParameter, ...] | None: ...


def get_tesseract_variables() -> set[str] | None:
    parameters = get_tesseract_parameters()
    return None if parameters is None else {p.name for p in parameters}
```

The parser keeps the existing guard (the first non-blank line ends with `:`)
and splits each row with `line.split("\t", 2)`. It accepts only rows with three
fields whose name matches `[A-Za-z0-9_]+`, and keeps engine order.
`get_tesseract_variables()` keeps its signature and failure semantics, so
`validation_error()` and its tests are unaffected, and the existing cached
test continues to exercise the single shell-out.

Alternative: let the dialog run the command itself. Rejected: two call sites
would duplicate the format guard, pay a second subprocess, and could disagree
about failure.

### Use `SimpleList`, not a new list widget

The dialog uses `SimpleList` with `Name`, `Default`, and `Description` columns.
It already provides columns, sorting, selection, and `row-activated`, and it
disables typeahead as the application requires. Name cells are made monospace
by setting the cell renderer's `family` property after the columns are built.

Alternatives:

- `Gtk.ColumnView` gives sortable columns but needs GTK 4.10.
- `Gtk.ListView` needs a GObject item type, an item factory, and a selection
  model: new machinery for one dialog.
- `Gtk.ListBox` is not virtualized, so hundreds of rows are heavier and its
  columns do not align.

### Filter by repopulating the model

`Gtk.SearchEntry`'s `search-changed` signal repopulates the `SimpleList` from
the cached rows, matching case-insensitively against
`f"{name} {default} {description}"`. GTK debounces `search-changed`, which
keeps fast typing cheap. An empty match set shows the "no parameters match"
label instead of a blank table.

Rows are sorted by name, case-insensitively, as the list is repopulated.
Sorting the view instead (`set_sort_column_id`) would wrap the store in a sort
model, while `SimpleList` reads selection paths against the raw model, so the
selected name could come from the wrong row. The source list is small at a few
hundred rows, so sorting on repopulation is cheap and keeps tests deterministic.

Alternative: insert a `Gtk.TreeModelFilter` between `SimpleList` and its store.
Rejected, because `SimpleList.data` and its callers assume the raw model.

### Dialog returns a name; controls write the field

`src/scantpaper/dialog/tesseractparams.py` defines
`TesseractParametersDialog(Dialog)`, constructed with:

- `parameters: Sequence[TesseractParameter] | None`
- `managed: Mapping[str, str]` (parameter name to owning-control label)
- `transient_for`

It exposes `selected_name: str | None`, set only when an insertable row is
chosen. `OCRControls` opens it with `run_dialog()` and, on
`Gtk.ResponseType.OK` with a non-`None` name, calls its own
`insert_variable(name)` and then `grab_focus()` on the field.

Alternatives: pass the buffer in (couples the dialog to `OCRControls`) or use a
callback (harder to reason about during a nested loop). A return value mirrors
other project dialogs and is easy to test.

Because `run_dialog()` waits on a response, the dialog MUST override
`_on_key_pressed` (Escape) and `_on_close_request` to emit
`Gtk.ResponseType.CLOSE`, as `MultipleMessage` does. Without that, Escape would
destroy the window and leave the loop running.

Keyboard focus is requested for the filter entry from a `map` handler, which
runs once the window is realized. `row-activated` (Enter or double-click) runs
the same insert guard as the button.

### Disable insertion instead of refusing it

The Insert button is insensitive unless the selected row is insertable. A
managed parameter therefore cannot produce an OK response at all, so the dialog
stays open and the field is never touched. The managed rows stay visible, and
their description gains a translated note, `Set by the %(control)s control`,
rather than a separate mostly-empty column.

Alternative: hide managed rows. Rejected, because the list would then claim to
be complete while validation still knows those names.

### Insertion rule

`OCRControls.insert_variable(name)`:

1. reads the buffer text before the cursor;
2. prefixes `\n` when that text is non-empty and does not end with `\n`;
3. inserts `f"{name}="` at the cursor, leaving the cursor after `=`;
4. does not insert a value.

The existing `variables` getter reads the buffer, so no extra state is updated.

### Placement

A right-aligned row below the variables view, inside the expander, holds an
`_Available parameters` button (`self._parameters_button` for tests). The row
and button exist only for the Tesseract branch, alongside the expander itself.

### Unavailable list

When `parameters` is `None`, the dialog shows a wrapped label saying the list
is unavailable and that OCR can still run, disables the filter and Insert, and
offers Close. The cached failure keeps that state stable for the session; this
change does not retry.

## Risks / Trade-offs

- Repopulating per keystroke could stutter on a slow machine. GTK's
  `search-changed` delay mitigates it; if it still shows, debounce further
  rather than replacing the model stack.
- Monospace names need a renderer tweak that `SimpleList` does not expose; the
  dialog sets it directly after construction.
- The tab-separated output format is assumed. If tesseract changes it, the list
  becomes unavailable, which is the same degradation validation already has.
- `lru_cache` caches a failure, so a fixed installation is only picked up on
  restart. Acceptable for an advisory browser.
- The nested `run_dialog` loop makes the Escape override mandatory, so it is a
  task, not optional polish.

## Migration Plan

No migration. Nothing is persisted; the feature writes into the existing text
field, which the current settings path already stores.

## Open Questions

None.
