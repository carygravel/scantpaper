## Context

See `proposal.md` — Why. Measured state of the codebase relevant to the
approach:

- `ruff check --select ANN` reports **7080 violations**: `ANN001` (3865,
  argument types), `ANN201` (1912, public return types), `ANN202` (1056,
  private/closure return types), `ANN003` (168, `**kwargs`), `ANN002` (79,
  `*args`). `ANN204/205/206` are already enforced and clean.
- Violations span **46 source modules, 76 test files (incl. `conftest.py`),
  and 2 `dev/` scripts**. Tests account for ~59% of violations, source ~41%.
- `ruff check .` and `ruff format --check .` run in all three
  `.github/workflows/test.yml` jobs, so the tree must stay green at every
  commit.
- The codebase is a typing blank slate today: no `Optional`/`Callable`/
  `TYPE_CHECKING`/`from __future__ import annotations` anywhere; only
  `collections.abc.Iterator` plus a few `NamedTuple`/`ClassVar` annotations
  (e.g. `basethread.py`). Forward refs are currently written as quoted
  strings (`Response.type: "ResponseType"`).
- `CONTRIBUTING.md` (Type Annotations) bans `typing.Any`; the code already
  follows this (`Response.info: object`, `basethread.py:25`).
- Verified safe to make annotations lazy: nothing in the repository calls
  `get_type_hints()`/`inspect.get_annotations()`, and all 45
  `@GObject.Property` sites pass an explicit `type=` argument.
- `ruff --check --select ANN --fix --unsafe-fixes --preview` mechanically
  inserts `-> None` on functions with no `return` statements (verified), and
  nothing else. Arguments must be annotated by hand.
- Coverage gate is 99% (`--cov-fail-under=99`). Annotations are not
  executable statements, so no coverage lines are added.

## Goals / Non-Goals

**Goals:**

- Every `def` in the scanned tree carries argument, `*args`/`**kwargs`, and
  return annotations, verified per module to `0` ANN violations.
- The five ANN codes leave the ruff `ignore` list only once the whole tree
  is clean, in a single final config-flip commit that CI then enforces.
- Adopt a single consistent annotation approach (lazy annotations, no
  `Any`, `TYPE_CHECKING` import blocks) so the result reads as a deliberate
  house style rather than 7000 one-off edits.

**Non-Goals:**

- Introducing a type checker (mypy/pyright) or new dependencies — this only
  satisfies ruff's ANN rules; the annotations become the future foundation
  for a checker, but none is added here.
- Changing any runtime behaviour, public API, or user-visible output.
- Re-architecting the GObject/threading patterns that are hard to type
  (e.g. the dynamic `do_<process>` dispatch in `BaseThread`).

## Decisions

### 1. Ratchet strategy: annotate first, flip the config last

The `ignore` list stays untouched through every annotation commit, so
`ruff check .` in CI cannot break mid-transition. Progress on each module is
verified with:

```bash
ruff check --select ANN <module>      # CLI select overrides the config ignore
```

must report `0` errors. The final commit removes `ANN001/002/003/201/202`
from `ignore` (plus the stale explanatory comment block) and is a pure
config change that CI's `ruff check .` then enforces permanently.

Alternatives considered:

- **Per-file-ignores whitelist ratchet** (codes active immediately, un-fixed
  files listed under `per-file-ignores`, peeled per module). Rejected: it
  starts as a ~120-entry whitelist, inverts the documented "ignore list is a
  blacklist to be ratcheted down" philosophy, and churns with every task.
- **Per-code ratchet** (enable `ANN002` → `ANN003` → `ANN201/202` →
  `ANN001`, one commit each). Rejected: `ANN001` (3865) and `ANN201+202`
  (2968) cannot be fixed in a single turn/commit, so code-grain commits are
  not achievable for the two largest codes. The module is the natural unit
  because a `def` needs its arguments *and* return annotated together.

### 2. Adopt `from __future__ import annotations` module-wide

PEP 563 makes every annotation lazy (stored as a string, resolved only by
`get_type_hints`/tools). Effect on this change:

- Forward references across the heavily cross-linked modules (e.g.
  `SimpleList`/`TiedList`/`TiedRow`, `BaseThread`/`Request`/`Response`,
  dialog classes, 76 test files) are written as plain names instead of
  quoted strings — the single biggest reduction in annotation-writing
  friction at this scale.
- Sequences like `Response.type: ResponseType` in `basethread.py` work
  without quotes or reordering.

Safety was verified: no runtime annotation readers exist, and all
`@GObject.Property` uses pass `type=` explicitly so property type inference
(a real PEP 563 casualty in PyGObject) is not relied on.

Trade-off: the import-time `NameError` safety net for annotation typos is
weakened (nothing resolves the strings). Ruff's static name resolution
(F821 and friends) mostly restores this, and is our enforced guard.

Alternative considered: keep eager annotations and quoted forward refs.
Rejected: quoting every cross-module reference across 7000 annotations is
exactly the tax this change would otherwise generate. `from __future__`
becomes default behaviour in Python 3.14 anyway (via PEP 649) — this sets
the convention early.

### 3. No `typing.Any`; `ANN401` stays enforced

Per `CONTRIBUTING.md` (and the existing `Response.info: object` precedent),
annotations never use `Any`:

- prefer the concrete type (gi repository classes for GTK, `sane.*` /
  `tesserocr.*` classes for untyped-but-real external objects),
- use a union of concrete types for genuinely multi-type values
  (`int | None`, `list | tuple | None`),
- use `object` for truly polymorphic payloads (callback payloads, pushed
  request attributes) so consumers narrow explicitly.

Because no `Any` is written, `ANN401` never fires and stays in the active
rule set — no new `ignore` entry needed. Rejected alternative: sanctioned
`Any` escape hatch plus `ignore ANN401`; it directly contradicts the
documented convention and the `AGENTS.md` quality gate ("type-annotated
without `typing.Any`").

### 4. GTK / thread / callback typing conventions

These recurring patterns get one house style each:

- **Signal handlers and closure callbacks** are annotated with the real gi
  types (`Gtk.CellRenderer`, `Gtk.TreeModel`, `Gtk.TreeIter`, `Gdk.Event`
  ...). Idle/IO/watch callbacks return `GLib.SOURCE_CONTINUE`/
  `GLib.SOURCE_REMOVE`, so their return type is `bool`.
- **Thread `*args`/`**kwargs` pass-throughs** (e.g. `BaseThread.__init__`,
  `Request.__init__`): `*args: object, **kwargs: object` — heterogeneous,
  forwarded wholesale; `send(process: str, *args: object, **kwargs: object)`.
- **Dynamic `do_<process>` dispatch** (`BaseThread.handler_wrapper`,
  `run`): the handler argument/return stay `object`/`bool` at the dispatcher
  boundary; the type-shape of each `do_*` method is annotated per method.
- **`@GObject.Property` getters/setters** get full signatures (getter
  `-> type`, setter `(self, value: type) -> None`); the decorator keeps its
  explicit `type=`.

### 5. Mechanical head-start per module

Run on each module before hand-annotating:

```bash
ruff check --select ANN <module> --fix --unsafe-fixes --preview
```

This inserts `-> None` on void functions only (functions with no `return`
statement — an accurate, reviewable transformation). Every machine edit is
reviewed with the hand-written ones; the whole module is then confirmed at
`ruff check --select ANN <module>` → `0`. The bulk of `ANN001/002/003` and
non-`None` `ANN201/202` is written by hand.

### 6. Execution order: leaf-first, pilot ahead

Module tasks run in dependency order so the annotation vocabulary is
established bottom-up, each task keeping CI green (config untouched):

1. **Pilot + conventions** — small leaf modules (`helpers`, `pagerange`,
   `loop_helpers`, `i18n`, `const`) settle the house style and produce the
   template diff the rest of the change follows.
2. **Leaf core** — `config`, `tesseract`, `text_layer_control`,
   `comboboxtext`, `entry_completion`, `progress`, `print_operation`, `app`,
   `scanner/*`, `frontend/*`, `postprocess_controls`, `dev/*`.
3. **Threads & IO** — `basethread`, `importthread`, `savethread`,
   `docthread`, `unpaper`.
4. **Core model** — `basedocument`, `page`, `document`, `bboxtree`,
   `simplelist`.
5. **UI** — `imageview`, `canvas`, `app_window`.
6. **Mixins** — file/edit/tools/scan menu mixins, `session_mixins`.
7. **Dialogs** — `pagecontrols`, `save`, `sane`, `scan`, `dialog/__init__`.
8. **Tests + conftest** — `src/scantpaper/tests/`, `conftest.py`
   (pytest fixtures annotated with their real types: `tmp_path: Path`,
   `pytest.MonkeyPatch`, mock/fixture objects, etc.).
9. **Config flip** — remove the five codes from `ignore`, update
   `CONTRIBUTING.md`, full `ruff check .` / `ruff format --check .` /
   `pytest`.

`from __future__ import annotations` and any `TYPE_CHECKING` import moves
(ruff's flake8-type-checking rules demand type-only imports move there once
annotations are lazy) land inside the same task as the module they belong
to, so every task is self-contained and reviewable. Runtime-used imports
(including `gi.repository`) stay at top level.

## Risks / Trade-offs

- **Un-annotated drift during the transition** — new `def`s added to a
  "finished" module before the flip would surface only at flip time.
  → Mitigation: single-author repo, low drift rate; the flip commit is a
  pure config change and CI's `ruff check .` catches anything missed.
- **`ruff` unsafe-fix misdirection** — `--unsafe-fixes` could insert a
  wrong `-> None` if a function has a `return` in a form ruff does not
  detect. → Mitigation: the `-> None` fix only fires on functions with no
  return statements; machine edits are always reviewed per module and
  re-verified to `0`.
- **PEP 563 weakens runtime type-error detection** — annotation typos no
  longer fail at import. → Mitigation: ruff statically resolves annotation
  names (F821) and is enforced in CI from the flip onward.
- **`@GObject.Property` inference breakage if someone omits `type=`** —
  later. → Mitigation: all current sites pass `type=`; `CONTRIBUTING.md`
  gains a note that property types must stay explicit under lazy
  annotations.
- **TC-rule churn** — moving type-only imports into `TYPE_CHECKING`
  blocks adds diff beyond the annotations themselves. → Anticipated and
  folded into each module task; it is the idiomatic end-state and cost is
  bounded per module.
- **Test-file noise** — ~59% of edits touch tests; large mechanical diffs.
  → Accepted: pure annotation edits, no behaviour change, and the existing
  `pytest-timeout`/coverage gates still run per task.

## Migration Plan

- No code ships until the flip, so every intermediate commit is
  behaviourally identical: `ruff check .` (with ANN still ignored), `ruff
  format --check .`, and `pytest` must all pass per task.
- Rollback: reverting the final config-flip commit restores the previous
  `ignore` list; earlier annotation commits are individually revertible and
  carry no behaviour change, so mid-transition rollback is always a clean
  revert.