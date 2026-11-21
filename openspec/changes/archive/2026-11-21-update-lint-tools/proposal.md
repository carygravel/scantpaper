# Proposal: update-lint-tools

## Why

`dev/lint-versions` pins ruff 0.16.7 and ty 0.0.85 so a new lint rule or ty
diagnostic cannot turn CI red without a deliberate bump. The scheduled
`lint-check` workflow now reports both tools blocked against the latest
releases (ruff 0.17.6, ty 0.0.107), and the pin has lost coverage of its
intended suppression: ty renamed `unresolved-attribute` to `missing-attribute`
and split off a new `missing-union-attribute` code, so the rule the project
deliberately ignores no longer matches. Both adoptions are mostly mechanical
— 28 conventional-import renames plus one class-attribute annotation on the
ruff side, and a config-key rename plus seven new diagnostics on the ty side —
so the pins are within one small change of `update-safe`, and letting them
drift further only compounds the same fixes later.

## What Changes

- **Bump the pins** in `dev/lint-versions` from `ruff=0.16.7` to
  `ruff=0.17.6` and from `ty=0.0.85` to `ty=0.0.107`, adopting the releases
  the `lint-check` workflow validates.
- **Migrate the ty rule config** in `pyproject.toml`: replace the
  `unresolved-attribute = "ignore"` key with `missing-attribute` (its renamed
  form) and add `missing-union-attribute = "ignore"` for the newly split-out
  code that covers the same GTK `None | Unknown` false-positive class the
  existing comment describes. This is the same suppression under ty's new
  naming, not a new blacklist entry.
- **Fix 29 new ruff findings**, all caused by rule-data changes upstream:
  - `ICN001`: rename `import datetime` to `import datetime as dt` in 28 files
    (safe — no file mixes `from datetime import` with a bare module import,
    and no file uses `dt` as another name).
  - `RUF012`: annotate `BaseThread.LiveThreads` with
    `ClassVar[weakref.WeakSet[BaseThread]]` (ruff 0.17.1 now treats
    `weakref.WeakSet` as a mutable class default).
- **Fix 7 new ty diagnostics** that survive the config migration, each a
  genuine new-check finding: 3 `invalid-assignment` in `bboxtree.py`, 1
  `unsound-return` in `canvas.py`, 2 `redundant-cast` in `simplelist.py`, and
  1 `truthiness-test-of-none-union` in a test file.
- No user-visible behaviour changes; this is developer-tooling adoption.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

(none — this change alters no application requirements: the
`linter-version` mechanism is unchanged, and this is pure tooling adoption,
so `skip_specs: true` is set in `.openspec.yaml`)

## Impact

- `dev/lint-versions`: the two version pins (the adoption itself).
- `pyproject.toml`: the `[tool.ty.rules]` key rename plus `missing-union-
  attribute`; no ruff config change is expected.
- Source: `basethread.py` (annotation), `canvas.py`, `bboxtree.py`,
  `simplelist.py`, and 28 files with a `datetime` import rename (spread
  across `src/scantpaper/`, `src/scantpaper/tests/`, and `dev/`).
- Tests: one `truthiness` fix in `test_0821_frontend_image_sane.py`.
- CI: no workflow change; `test.yml` and the scheduled `lint-check` both read
  the pins, so they adopt the new tools automatically and the issue closes
  once the pins match `latest`.
- Verification: `ruff check .`, `ruff format --check .`, `ty check .`,
  `pytest`, the coverage gate, and the OpenSpec validation all pass with the
  bump in place.
