## Context

Pylint is a phantom gate: installed via `python3-pytest-pylint` in only the
`latest_w_ppa` CI job, unconfigured (no pytest config turns it on), and green on
`main` regardless of `pylint.txt`. Ruff already lints the full codebase in zed
and `ruff check .` passes clean on the current tree with the existing
`pyproject.toml` config. See `proposal.md` — Why for the motivation.

**Key constraint** (from the request): ruff is not packaged in Debian (only
pulled in by zed), so it must NOT be added to `pyproject.toml` (which feeds the
`.deb` build). It is installed via `pip` in the CI jobs that already use pip.

## Goals / Non-Goals

**Goals:**
- Ruff becomes the single, enforced linting gate in CI (all jobs).
- Ruff also replaces black as the formatter (lint + format from one tool).
- Pylint, black, and all their bookkeeping are removed from the repo.
- `ruff check .` and `ruff format --check .` are green in CI on the current tree.

**Non-Goals:**
- Ratcheting down the `ignore` list — out of scope; tracked separately.
- Matching black's formatting byte-for-byte. `ruff format` output differs
  cosmetically on this codebase (46 files); the one-time reformat is accepted
  as part of the migration.
- Adding ruff to `pyproject.toml` dependencies (Debian packaging constraint).
- Introducing type checking (mypy) — still disabled in tox.

## Decisions

**D1 — Install ruff via pip in every CI job.**
All three jobs in `.github/workflows/test.yml` (`latest_w_ppa`, `latest`,
`oldest`) already use pip. Add `pip install ruff` (pinned to `0.16.5`, matching
the version zed uses, for reproducibility), a `ruff check .` step, and a
`ruff format --check .` step after it (replacing the current `black --check .`).
- *Alternative considered:* rely on the ruff already in the venv — rejected; CI
  environments are fresh and need their own install.
- *Why pin:* black was pinned (`26.3.1`); consistent with that practice and
  avoids surprise rule/format changes when ruff bumps.

**D2 — Keep the current `ignore` list unchanged for this change.**
`ruff check .` is already green, so the ruff gate passes with zero fixes. No
rule is removed from `ignore` here; ratcheting is deferred (see Risks).
- *Alternative considered:* also fix `D`/`ANN` docstring and annotation rules.
  Rejected — that is a large, separate effort and would bloat this change.

**D3 — Delete `.pylintrc` and the report files.**
`.pylintrc` (12 lines: `extension-pkg-allow-list` for `_sane,gi,cairo,
tesserocr` + `generated-members` suppressing GTK `E1101`) is obsolete. Its
unique value — dynamic-member suppression — does not map to ruff, which does no
type inference; ruff simply never raises those checks. `pylint.txt` /
`pylint.txt.new` are the score-tracking reports and go away with the gate.

**D4 — In `dev/generate_pot.py:18`, keep `# noqa: E402`, drop `pylint: disable`.**
The line currently carries both `# pylint: disable=wrong-import-position,
import-error` and `# noqa: E402`. ruff needs only the `noqa`; the pylint clause
is removed.

**D5 — Docs update, not removal of gate language.**
`AGENTS.md`, `CONTRIBUTING.md`, `openspec/config.yaml` replace "pylint-clean /
do not increase pylint warnings" with "ruff-clean / `ruff check .` passes", and
black-referencing formatter text with `ruff format`. The lint-suppression-approval
rule (ask before adding `noqa`) is preserved and reworded for ruff.

**D6 — Replace black with `ruff format`.**
Drop `black==26.3.1` from the `test` extras in `pyproject.toml`, delete
`.pre-commit-config.yaml` (its black hook is superseded), and swap the CI
`black --check .` steps for `ruff format --check .`. Run a one-time `ruff format`
over the tree to apply the new output. Empirically `ruff format` differs from
black on 46 files (7 source + 36 test + 3 archived-markdown code blocks); the
diffs are cosmetic parenthesization (e.g. assert-message wrapping) and are
accepted as a mechanical migration.
- *Why ruff over black:* one tool for lint + format, faster, and ruff's
  formatter is designed as a black drop-in (same 88-char default).
- *Why not keep black:* two formatters is redundant; the whole point is to
  collapse lint + format onto the single pip-installed ruff binary.
- *Note:* `ruff format` parses Python code blocks inside `.md` files. To keep
  the CI `ruff format --check .` from gating on the *historical* records under
  `openspec/changes/archive/`, add `[tool.ruff.format] exclude = ["openspec"]`
  so formatting governs only actual Python source (see D7).

**D7 — Exclude the `openspec/` docs tree from ruff formatting.**
Ruff formats fenced Python in markdown. The archived change records under
`openspec/changes/archive/` should not be reformatted by this migration. Add
`[tool.ruff.format] exclude = ["openspec"]` to `pyproject.toml` so `ruff format
--check .` targets only real Python. Lint already ignores `openspec` (no Python
to lint there), so only the format section needs the exclude.

## Risks / Trade-offs

- **[Loss of pylint's dynamic-member checks]** → Not real signal here: the
  `.pylintrc` existed to *suppress* `E1101`, and the remaining pylint report is
  dominated by `R09xx`/`C03xx` complexity checks that ruff equivalents already
  cover (and that are in the ignore list). No behavioral coverage is lost.
- **[ratcheting never happens, ignore list stagnates]** → Deferred intentionally;
  the proposal records it as follow-up, and the `ignore` list's own comment
  ("to be ratcheted down") documents the intent.
- **[CI depends on pip-installed ruff, which is not in Debian]** → Acceptable:
  the affected CI jobs are pip-based. The `.deb` build (`deb.yml`) only needs
  `python3-pytest-pylint` *removed*; it never required ruff at build time.
- **[one-time `ruff format` reformats 46 files → large diff, review burden]**
  → The reformat is mechanical and the diff is confined to `scantpaper/` +
  `scantpaper/tests/`; the archived `openspec/` docs are excluded (D7) and not
  mutated. All formatting changes are verified by `ruff format --check .` and
  the full `pytest` suite.
- **[unpinned ruff drifts]** → Mitigated by pinning to `0.16.5` in D1.