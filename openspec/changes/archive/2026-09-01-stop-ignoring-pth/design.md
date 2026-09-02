## Context

See proposal.md - Why. In short: 193 PTH violations, not "60k lines" as the config comment claims. The stack is Python 3.10+, ruff 0.16.5 (editor-time only, not a CI gate), and the suite enforces 99% coverage via `--cov-fail-under=99`. Black (26.3.1) is enforced in CI (`black --check .`); pylint runs via `pytest-pylint` in CI.

Full current violation breakdown (ruff 0.16.5):

| Rule | Meaning | Count | Fixable? |
|------|---------|-------|----------|
| PTH123 | builtin `open()` | 47 | preview-safe (46) / preview-unsafe (1) |
| PTH107 | `os.remove` | 19 | preview-safe |
| PTH120 | `os.path.dirname` | 16 | preview-unsafe |
| PTH207 | `glob` | 15 | **none** |
| PTH118 | `os.path.join` | 14 | **none** |
| PTH101 | `os.chmod` | 13 | preview-safe |
| PTH100 | `os.path.abspath` | 12 | preview-unsafe |
| PTH113 | `os.path.isfile` | 12 | preview-safe |
| PTH202 | `os.path.getsize` | 12 | preview-safe |
| PTH110 | `os.path.exists` | 7 | preview-safe |
| PTH112 | `os.path.isdir` | 5 | preview-safe |
| PTH109 | `os.getcwd` | 5 | preview-unsafe |
| PTH108 | `os.unlink` | 5 | preview-safe |
| PTH116 | `os.stat` | 4 | preview-unsafe |
| PTH111 | `os.path.expanduser` | 2 | preview-unsafe |
| PTH104 | `os.rename` | 2 | preview-safe |
| PTH114 | `os.path.islink` | 1 | preview-safe |
| PTH106 | `os.rmdir` | 1 | preview-safe |
| PTH102 | `os.mkdir` | 1 | preview-safe |

**Total: 193. 164 autofixable with `--preview --fix` (124 safe, 40 unsafe). 29 require manual work (PTH118 + PTH207).**

## Goals / Non-Goals

**Goals:**
- Remove `"PTH"` from the `ignore` list in `pyproject.toml` and get a clean `ruff check` to zero PTH violations.
- Let ruff autofix the mechanical bulk, with `--unsafe-fixes` where semantic review is cheap.
- Keep the 99% coverage gate green and pylint warning count flat.

**Non-Goals:**
- Migrating `os.chdir`/`os.access`/`os.getcwd`-adjacent non-PTH code (PTH covers only listed rules).
- Rewriting string-path APIs to pure `Path` types end-to-end (the long-term goal) — this change only stops ignoring PTH. Call sites that still pass `str` (e.g. via `pikepdf`, `ocrmypdf`, GTK file choosers) stay `str`; only the path *handling* moves to pathlib.

## Decisions

### D1: Run `ruff check --select PTH --preview --fix --unsafe-fixes`
Ruff 0.16.5 gates ALL PTH autofixes behind `--preview`. Without `--preview`, **zero** autofixes run. With it, 164/193 resolve automatically.
- **Alternatives considered:** (a) manual-only migration — too slow for ~170 mechanical lines; (b) `--fix` without `--preview` — does nothing, verified empirically; (c) upgrade pinning a newer ruff — not justified for 164 fixes that already exist in preview.

After the automated pass, *review every changed hunk* — the unsafe fixes rewrite semantics in ways the diff shows clearly (e.g. `os.path.abspath` → `Path.resolve()`, which also resolves symlinks).

### D2: Split into two sequential passes: safe fixes, then unsafe fixes
Two passes with a review checkpoint between them:
1. `--preview --fix` (safe only) → 124 violations resolved, semantically clean.
2. `--preview --fix --unsafe-fixes` → 40 more resolved. Each of these needs a human/eyeball review of the hours-spent-on-resolution line (PTH100 abspath→resolve, PTH120 dirname→parent, PTH116 stat, PTH109, PTH111).
- Both passes auto-add `import pathlib` where needed. Ruff emits fully-qualified `pathlib.Path(...)` rather than bare `Path`; that's acceptable — a follow-up cleanup pass (bare `Path` import) can happen under the long-term "whole codebase on pathlib" effort, not this change.

### D3: Manually handle the 29 non-autofixable sites
These are the only real judgment calls:
- **PTH118 (`os.path.join`, 14 sites)** — needs `Path(a) / b` rewrite by hand.
- **PTH207 (`glob`, 15 sites)** — `Path.glob`/`Path.rglob` return `Path` objects, not `str`; every consumer must be checked for string assumptions (`subprocess.run([...], x)`, `x + ".h"`, sorting/index-matching in `importthread._correlate_pdf_images`, recursive slurps, `file_menu_mixins` concatenating two glob results).
- **PTH123 (1 unsafe site)** — `open(..., "x")`-adjacent? Actually no `"x"` mode found; but one site converts under unsafe (currently in `session_mixins.py:80` cross-scope lockfile handle which already carries `noqa: SIM115`). Review that one individually.

### D4: Keep the `noqa: SIM115` on the lockfile handle
The `Path.open()` conversion does not remove the cross-scope-handle concern; retain the existing suppression comment and verify the `# noqa: SIM115` still targets the right rule after the rewrite.

### D5: Fix the config comment
The `ignore` entry's comment claims "60k lines still use os.path everywhere" — demonstrably false (193 violations). Replace it with an accurate count and a note that PTH will now be enforced, so the ratchet stays shut.

### D6: Verification gate
- `ruff check .` → zero PTH (and no new errors elsewhere).
- `black --check .` → clean (run after autofix; black can normalize the generated style).
- `pytest` → all green incl. the 99% coverage floor.
- `pylint` baseline → warning count must not increase.

## Risks / Trade-offs

- **[PTH100 `abspath` → `Path.resolve()`]** → `resolve()` also normalizes symlinks and collapses `..`; if any site relies on non-resolving behavior, keep `os.path.abspath` and add a targeted per-file-ignore or `# noqa` (approved per AGENTS.md). Mitigation: review the 12 unsafe hunks individually; they appear in the diff pass.
- **[PTH120 `dirname` → `parent`]** → `os.path.dirname("a")` returns `""` but `Path("a").parent` returns `"."`. Corner-case semantics differ. Mitigation: spot-check every converted `dirname` for the empty-string edge; prefer `.parent` only where a trailing slash/`.` is acceptable to downstream code.
- **[PTH207 `glob` str→Path ripple]** → consumers may concatenate strings, sort, or index-match returned items. Mitigation: fix these 15 manually (D3) with per-consumer review; this is the highest-risk cluster of the change.
- **[`--unsafe-fixes` over-applies]** → `--unsafe-fixes` may touch hunks outside the intended 40. Mitigation: run `--diff` first to stage expectations, then apply, then review the diff; rely on `git diff` review before commit.
- **[Coverage gate dips]** → a conversion that changes a branch (e.g. exception type or a `Path`-vs-str edge) could lower coverage. Mitigation: run `pytest` after each pass; the failing-path coverage is concentrated in tests already.

## Migration Plan

1. Baseline `git stash`/note: capture `ruff check --select PTH --statistics` and `pylint` warning count before starting.
2. D1a: `ruff check --select PTH --preview --fix` (safe 124) — then `ruff check` full to confirm no other rule regressions.
3. Verify: `black --check .`; `pytest`; review the git diff for the 124 safe hunks (low risk, skim).
4. D1b: `ruff check --select PTH --preview --fix --unsafe-fixes` (40) — review each unsafe hunk.
5. D3: manually resolve the 29 remaining (PTH118 ×14, PTH207 ×15) with consumer review.
6. D5: update the `pyproject.toml` comment; remove `"PTH"` from `ignore`.
7. Full gate: `ruff check .` clean, `black --check .`, `pytest` (incl. coverage >=99%), pylint flat.
8. Rollback: revert is a plain `git revert` — no data/migration/state to unwind; this is pure code refactor.

## Open Questions

- None blocking. The 1 unsafe `open()` site (PTH123) and the exact set of `glob` consumers to string-convert are judged during implementation, per D2/D3, and don't change the approach or task breakdown.