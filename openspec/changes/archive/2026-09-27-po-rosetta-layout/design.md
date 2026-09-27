# Design: Restructure translation catalogs for Launchpad Rosetta

## Context

See proposal.md — Why. Currently catalogs live flat as `po/scantpaper-<lang>.po`,
the pot is written to `scantpaper.pot` in the process's current directory, and
every tool that needs a language code parses the `scantpaper-` filename prefix.
The change moves catalogs into a Rosetta-compliant template directory and makes
the tools derive language and domain from the new layout.

## Goals / Non-Goals

Goals:
- Source tree, tooling and default pot path match Rosetta's layout with no
  manual restructuring at upload time.
- Domain and language are derived from the directory name and filename stem,
  removing the `scantpaper-` prefix parsing.
- All existing checks (`check_po.py`, the po test suite) keep passing.

Non-Goals:
- Compiling/installing `.mo` into the wheel (a pre-existing, separate gap).
- Supporting multiple templates; the layout leaves room for it but this
  change only introduces the single `scantpaper` template directory.
- Committing the generated pot (it stays a gitignored build artifact).

## Decisions

- **One template directory named after the domain.** `po/scantpaper/` holds
  `scantpaper.pot` plus `<lang>.po`. This mirrors Rosetta's
  `template1/template1.pot` + `template1/de.po` exactly and gives a natural
  home for any future templates (`po/<other>/`).
- **Domain from the parent directory name, language from the filename stem.**
  `po/scantpaper/de.po` → domain `scantpaper`, language `de`. Rationale: the
  domain is no longer embedded in the filename, and the directory name is the
  only place it lives; it also matches how Rosetta groups files.
  Alternatives considered: hardcoding/`--domain` in every tool (rejected —
  duplicates the mapping and can drift); keeping the `scantpaper-` prefix in
  filenames (rejected — that is exactly the flat layout Rosetta rejects).
- **`generate_pot.py` gains `--output`, defaulting to
  `po/scantpaper/scantpaper.pot` resolved against the repo root**, creating
  parent directories. Rationale: `check_po.py` and the tests must keep
  generating into a temporary directory (to avoid clobbering the real pot), so
  an explicit override is required; a repo-root-resolved default means a bare
  `dev/generate_pot.py` from anywhere writes to the canonical location.
- **`check_po.py` keeps its temp-dir generation**, now passing
  `--output <tmp>/scantpaper.pot`. The temporary generation is unchanged in
  spirit; only the invocation changes.
- **`compile_mo.py` derives the domain from the parent directory name** when
  no `--domain` is given, keeping `--domain` as an explicit override. This
  preserves the current `--src po --out ... --domain scantpaper` behaviour at
  the new path.

## Risks / Trade-offs

- **Breakage from path churn** (44 files moved, 5 tools/tests updated) →
  mitigated by keeping the move purely mechanical (a single `git mv`), running
  the full `check_po.py` + po test suite after the change, and keeping every
  tool's `--src`/`--output` overridable so behaviour is testable.
- **Domain inference is a new convention** that could surprise contributors →
  documented in README and AGENTS.md, and embodied in `compile_mo.py` so there
  is one source of truth.
- **Pot default path depends on repo-root resolution** rather than cwd →
  resolved from the script's own location so running from any directory is
  deterministic; tests and `check_po.py` override with `--output`.

## Migration Plan

1. `git mv` the 44 catalogs into `po/scantpaper/`; leave
   `po/TRANSLATION-FINDINGS.md` in place.
2. Update the four dev scripts and the test module to the new paths and the
   new domain/language derivation.
3. Update `.gitignore`, README and AGENTS.md.
4. Regenerate the pot at the new default path and run `check_po.py` and the po
   tests to confirm zero errors and a passing suite.
5. Rollback is a simple `git revert`/`git checkout` of the moved files; no
   data is lost and no migration of existing translations is required.

## Open Questions

None.
