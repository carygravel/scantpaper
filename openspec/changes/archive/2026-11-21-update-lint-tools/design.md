# Design: update-lint-tools

## Context

See `proposal.md` — Why for motivation. `dev/lint-versions` pins ruff 0.16.7
and ty 0.0.85; the lint-check workflow reports `update-blocked` for
ruff 0.17.6 (29 findings) and ty 0.0.107 (411 diagnostics, of which 403 are
one rule and 7 are individual new checks).

The blockers decompose into four distinct upstream causes, each with its own
fix shape:

1. **ruff 0.17.0** (breaking, PR #28790) added `datetime` → `dt` to the
   `ICN001` conventional-alias list: 28 bare `import datetime` sites.
2. **ruff 0.17.1** (PR #29213) now treats `weakref.WeakSet` as a mutable
   class default: `basethread.py:119` (`LiveThreads = weakref.WeakSet()`).
3. **ty** renamed `unresolved-attribute` → `missing-attribute` and split off
   a new `missing-union-attribute` code (ty #2471, PR #29944). The existing
   `[tool.ty.rules]` key still aliases `missing-attribute` but no longer
   covers `missing-union-attribute`, which is precisely the GTK
   `None | Unknown` false-positive class that key was written to suppress —
   403 diagnostics flood back.
4. **ty 0.0.10x** added seven individual new checks (`invalid-assignment`,
   `unsound-return`, `redundant-cast`, `truthiness-test-of-none-union`) that
   fire on real code.

Verified locally in a throwaway venv mirroring `lint-check.yml`
(`.[test]` plus latest tools): with the ty rules updated (cause 3), ty drops
to exactly the 7 individual diagnostics; each has a distinct, minimal fix.
The project `.venv` is *not* authoritative for these runs (stale pytest
7.4.4 without typed stubs changes ty's resolution) — the throwaway venv
under `/tmp/opencode/ci-faithful` is the faithful reproduction.

## Goals / Non-Goals

**Goals:**

- Make both pins `update-safe`: ruff 0.17.6 and ty 0.0.107 pass
  `ruff check`, `ruff format --check` and `ty check` against the repository.
- Preserve the suppress-on-`None | Unknown` decision from the old ty config
  under the new rule names (a migration, not new suppression).
- Change no user-visible behaviour: every fix is import/annotation/cast/
  type-hint work plus two truthiness equivalents in a test.
- Land the pins and source changes together so CI never runs a broken
  combination.

**Non-Goals:**

- Fixing the `linter-version` mechanism itself (spec unchanged; `skip_specs`).
- Reverting, relaxing, or reconfiguring the ruff `select = ["ALL"]` posture.
- Touching the ruff `ignore` blacklist — the 29 findings are all acceptable
  upstream conventions, not project noise.
- Re-annotating the GTK widget layer to eliminate `None | Unknown` (the
  longstanding, separately-tracked ratchet; not needed for the bump).
- Upgrading to a partial/later ruff or ty point release to dodge a rule —
  adopt the validated `latest`.

## Decisions

- **TY RULE MIGRATION — replace `"unresolved-attribute" = "ignore"` with
  `"missing-attribute" = "ignore"` and add
  `"missing-union-attribute" = "ignore"` in `[tool.ty.rules]`, applied
  ATOMICALLY with the pin bump.**
  `missing-attribute` is the renamed key; `missing-union-attribute` is the
  split-out code covering attribute access on a union where some (not all)
  members lack it — the exact `None | Unknown` GTK-widget false-positive
  class the existing comment describes. Keeping both on `ignore` preserves
  the project's documented decision; it is not a new blacklist entry.
  The migration is version-bound: the new key names are unknown to ty
  0.0.85 (two `unknown-rule` warnings, exit 1) while the old key name trips
  a `renamed-rule` warning under ty 0.0.107 — verified, no single config
  passes both versions, and `renamed-rule = "ignore"` does not suppress the
  warning. So the migration lands in the same commit as the pin bump; the
  repository keeps the old config (and stays green under pin 0.0.85) until
  that atomic step. Source fixes are verified in the meantime with
  command-line `-c "rules.missing-attribute = 'ignore'" -c
  "rules.missing-union-attribute = 'ignore'"` overrides on ty 0.0.107,
  which simulate the post-bump config without editing the file.
  Alternatives considered: leave `missing-union-attribute` at
  `all = "error"` and genuinely fix all 403 — rejected (they are the class
  the comment already deemed noise without per-widget annotations, and
  fixing them is the separate ratchet work); blanket `# ty: ignore` at the
  403 sites — rejected (AGENTS.md forbids blanket suppression without
  approval, and this is a configuration migration, not a code change).

- **DATETIME IMPORT ALIAS — rename `import datetime` → `import datetime as
  dt` in all 28 sites (ruff autofix), keep the `dt` references.**
  Verified: no file mixes `from datetime import …` with a bare module
  import, no file uses `dt` for anything else, and ruff's `--fix
  --unsafe-fixes` rewrites usages too (`datetime.datetime.now()` →
  `dt.datetime.now()`). One test already uses the alias. The project
  convention (AGENTS.md: `import` statements carry conventional aliases)
  favours adopting the upstream default rather than fighting it.
  Alternatives considered: add `ICN001` to the ruff `ignore` list — rejected
  (the rule is valuable and the fix is mechanical); configure
  `extend-aliases` — rejected (`datetime` is already in the default set; the
  natural reading is to adopt it).

- **RUF012 — annotate `LiveThreads` as
  `ClassVar[weakref.WeakSet[BaseThread]] = weakref.WeakSet()`.**
  The comment (and `__init__` use `self.LiveThreads.add(self)`) shows it is
  an intentionally shared class-level registry, so `ClassVar` is the
  truthful annotation; verified it silences RUF012 on both versions.
  Alternatives considered: assign it per-instance in `__init__` — rejected
  (it is a process-wide live-thread registry that tests iterate to quit
  lingering threads; per-instance would change behaviour); `# noqa` —
  rejected (blanket suppression).

- **BBOXTREE `invalid-assignment` — pin the heterogeneous dict's element
  type at the assignment sites so ty stops narrowing it to a single shape.
  Expected shape: annotate the fresh empty dicts in
  `PDFTextParser.handle_starttag` (and any other branch that rebinds
  `self.data = {}`) as `dict[str, object]`, matching `HOCRParser.__init__`'s
  declaration. If ty still narrows through the `self.data = self.stack[-1]`
  rebindings, fall back to the file's existing `cast("dict[str, object]",
  …)` idiom at the three subscript assignments.
  The three sites (`"type" = tag` twice, `"text" = data`) all store a `str`
  into a dict the surrounding branches fill with `list[float]` bboxes; the
  dict is deliberately heterogeneous. The fix restores the declared type
  rather than changing data flow.
  Alternatives considered: `# ty: ignore` at the three lines — rejected
  (blanket suppression); widening to `dict[str, object]` *only* at the
  subscript sites with a cast — accepted as the fallback, preferred fix is
  the annotation so the whole branch stays typed.

- **CANVAS `unsound-return` — declare the element type once so the
  `first_bbox` reassignment keeps it. Expected shape: annotate
  `self._bbox: list[Bbox]` where `TreeIter` first assigns it in `__init__`,
  so `self._bbox = [self._bbox[0]]` and the `return self._bbox[0]` stay
  `Bbox`. If ty still reports unsoundness from the reassignment, use the
  file's established `cast("Bbox", …)` idiom (already used at lines 1836–
  1837) on the return. `TreeIter` is constructed with a non-empty `[bbox]`
  and `first_bbox` is only called on a live iterator, so the runtime is
  already sound; this is a typing fix only.
  Observed during implementation: the annotation did not need the fallback
  cast, but it exposed five further `redundant-cast` diagnostics ty had
  previously missed (lines 1870, 1882, 1919, 1963, 1969) — with the
  element type known, `child`, `sibling`, `parent` and `self._bbox[-1]`
  are provably `Bbox`, so those `cast("Bbox", …)` wrappers were deleted as
  well (same behaviour-identical rationale as the SIMPLELIST casts).
  Alternatives considered: `# ty: ignore[unsound-return]` — rejected.

- **SIMPLETLIST `redundant-cast` — delete the two `cast(...)` wrappers.**
  ty proves the expressions are already `Iterator[object]` and
  `Iterator[list[object]]` respectively, and `typing.cast` is a runtime
  no-op, so removal is behaviour-identical. The `Iterator[object]` and
  `Iterator[list[object]]` return annotations stay as they are.

- **TEST TRUTHINESS — change `if r.exc_info` to `if r.exc_info is not
  None` in `test_0821_frontend_image_sane.py`.**
  `r.exc_info` is a three-tuple or `None`; a non-`None` three-tuple is always
  truthy, so the semantics are identical and the new `truthiness` check is
  satisfied. Provides the logged-response list, so it must keep matching any
  record with a traceback.

## Risks / Trade-offs

- [Bboxtree/canvas type-narrowing fixes are subtle; ty's inference is the
  arbiter] → The design deliberately picks annotation-first, cast-fallback
  idiomatic shapes; the implementation task verifies each against the same
  throwaway venv and abandons a shape that does not clear the diagnostic
  rather than suppressing it.
- [The 28-file import rename collides with in-flight changes
  (`fix-default-lineart-not-binarized`, `resample-bilevel-and-palette-pages`
  are in progress)] → Keep the rename purely mechanical (ruff autofix +
  review), land it in one commit, and re-run `pytest` to catch any
  collision; the touched files are test and scanning-side modules unlikely
  to overlap.
- [The maintainer must explicitly approve extending `[tool.ty.rules]`] →
  This is a migration of an existing entry, not a new suppression; the
  proposal, design, and the diff comment together carry that rationale for
  review rather than slipping it through.
- [Regression: behaviour must be identical after type-only edits] →
  Every change is import-alias, annotation, cast-removal or `is not None`;
  guarded by the full suite (`pytest`, coverage gate).

## Migration Plan

1. Apply the SOURCE and TEST fixes (imports, annotations, cast removal,
   `is not None`). `pyproject.toml` and `dev/lint-versions` are **not**
   changed yet — the repository stays green under the pinned tools
   (0.16.7 / 0.0.85) at every intermediate commit.
2. Verify each source fix against the **new** ty 0.0.107 in the throwaway
   venv using command-line overrides that simulate the post-bump config
   (`-c "rules.missing-attribute = 'ignore'" -c
   "rules.missing-union-attribute = 'ignore'"`), so a fix is proven against
   the tool it targets without editing the config file early. Also confirm
   the source fixes stay clean under the OLD pin (0.0.85 + old config) in a
   faithful venv, so the old gate is never red.
3. Atomically: migrate `[tool.ty.rules]` to the new key names AND bump
   `dev/lint-versions` to `ruff=0.17.6` / `ty=0.0.107` in the same commit.
   This is the only step that changes the config, because the config is
   version-bound to the new ty.
4. Full gates: `ruff check .`, `ruff format --check .`, `ty check .`,
   `pytest`, `dev/check_test_coverage.py`,
   `openspec validate --specs --strict --no-interactive`,
   `openspec validate --archived --no-interactive` — all with the bumped
   pins installed.
5. Push. `test.yml` picks the new pins up automatically; the scheduled
   `lint-check` flips the issue to `safe to upgrade` and closes it once the
   pins match `latest`.

Rollback: revert the two pin lines (a one-line revert returns CI to the
known-green 0.16.7/0.0.85). The source fixes are themselves compatible with
older tools (annotations and aliases are accepted by 0.16.7/0.0.85, and
cast removal / `is not None` were already clean under them), so no source
revert is needed to roll the pins back.

## Open Questions

None — every diagnostic has a decided, verifiable fix shape; any surprise
that surfaces during implementation (a type-narrowing shape that does not
clear the diagnostic) is a fallback already written into the decision
rather than a spec- or task-affecting unknown.
