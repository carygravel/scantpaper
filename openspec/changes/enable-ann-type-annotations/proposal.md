## Why

The `ruff` `ignore` list in `pyproject.toml` exempts the flake8-annotations
rules `ANN001`, `ANN002`, `ANN003`, `ANN201` and `ANN202`, so argument,
`*args`/`**kwargs`, and return type annotations are not enforced anywhere in
the codebase. A full scan reports 7080 missing-annotation violations across
source, tests, and dev scripts. Only the purely mechanical special/static/
classmethod return rules (`ANN204/205/206`) are currently enforced. This
change annotates the entire codebase and ratchets the remaining ANN rules on,
so that typing is enforced continuously from that point on.

The change is purely an internal quality-gate change: no user-visible
behaviour, data model, or dependency changes.

## What Changes

- Add type annotations (arguments, `*args`, `**kwargs`, and return types)
  to every function, method, and closure across:
  - `src/scantpaper/` source (`46` modules),
  - `src/scantpaper/tests/` including `conftest.py` (`76` files),
  - `dev/` scripts (`2` files).
- Adopt `from __future__ import annotations` module-wide so forward
  references across the heavily cross-linked modules need no string quoting,
  and move type-only imports into `if TYPE_CHECKING:` blocks where ruff's
  flake8-type-checking rules require it (verified: no runtime code in the
  project reads `__annotations__`; all `@GObject.Property` sites pass an
  explicit `type=`, so nothing breaks).
- Annotate with concrete types only. Per `CONTRIBUTING.md`, `typing.Any` is
  not used anywhere — polymorphic payloads use `object` (the pattern already
  used by `Response.info: object` / `Response.pending: object`), and
  multi-type values use `X | Y` unions. `ANN401` remains enforced and is not
  added to the `ignore` list.
- Remove `ANN001`, `ANN002`, `ANN003`, `ANN201` and `ANN202` from the ruff
  `ignore` list — the `ignore` list is a documented "blacklist to be
  ratcheted down", and this change is the final ratchet for the ANN family.
  The config flip is the last commit, only after `ruff check .` is clean.
- Update `CONTRIBUTING.md` to document the adopted annotation conventions
  (module-wide `from __future__ import annotations`, `TYPE_CHECKING` import
  blocks, GTK callback typing) and the now-enforced ANN rules.

## Capabilities

_This change is pure tooling/code-quality work: it alters no user-visible
behaviour, so `skip_specs: true` is set in `.openspec.yaml` and no capability
specs are created or modified._

### New Capabilities

- None.

### Modified Capabilities

- None.

## Impact

- **Code:** every module in `src/scantpaper/` (46), every file in
  `src/scantpaper/tests/` (76, plus `conftest.py`), and the `dev/` scripts
  (`dev/compile_mo.py`, `dev/generate_pot.py`).
- **Config:** `pyproject.toml` — `[tool.ruff.lint]` `ignore` list
  (`ANN001/002/003/201/202` removed) and the explanatory comment block.
- **Docs:** `CONTRIBUTING.md` (annotation conventions). `README.md` is
  unaffected — nothing user-visible changes.
- **CI:** `ruff check .` and `ruff format --check .` run in all three
  `.github/workflows/test.yml` jobs and become the permanent enforcement gate
  for these rules once the config flip lands.
- **No new Python dependencies**; the `typing` module is stdlib.
- Type annotations are not executable statements, so the existing `99%`
  coverage gate is unaffected.