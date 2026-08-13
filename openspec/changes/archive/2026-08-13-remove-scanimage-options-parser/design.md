## Context

See proposal.md - Why for the motivation. Current state:

- `scanner/options.py` has two construction paths: the list branch (python-sane tuples) used by every production caller, and the string branch (`_parse_scanimage_output`) used only by the `test_02_*` tests.
- The parser pulls in a chain of helper functions and constants, all with no production callers.
- `within_tolerance` is live production code (`dialog/scan.py:1256`) but its only direct test coverage lives in `test_02_scanner_options_test.py`, which feeds it via the parser.
- `delete_by_index`, `delete_by_name`, `by_title`, and the `device` attribute have no production callers.
- Coverage must stay at/above 98% (`--cov-fail-under=98` in `pyproject.toml`), and uncovered/partially-covered lines must not increase (AGENTS.md).

## Goals / Non-Goals

**Goals:**
- Remove all dead scanimage/scanadf text-parsing code and its test fixtures.
- Keep live-production functions (`within_tolerance`, `supports_paper`, `parse_geometry`, `can_duplex`, `flatbed_selected`, `num_options`, `by_index`, `by_name`, `val`) fully covered.
- Relocate rescued tests out of the legacy `test_02_*` naming.

**Non-Goals:**
- Touching `profile.py` (`map_from_cli` / `map_to_cli`) — those map CLI *option names* (l/t/x/y) for backward compatibility with pre-v3 profiles; they do not parse scanimage text.
- Migrating the fixture data into python-sane format (Thread B) — the real-device captures carry no regression value once the parser is gone.
- Changing any user-visible scanner behavior.

## Decisions

**D1: Non-list input to `Options.__init__` raises `TypeError`.**
The string branch disappears entirely. `Options` accepts only a list of option descriptors (tuples or `Option` namedtuples). Passing anything else is a programming error.
- Alternative considered: accept a string and silently return an empty options array (the current `Options("")` behavior). Rejected — silently swallowing bad input hid the error; an explicit `TypeError` follows ruff `TRY004` (prefer `TypeError` for type-checking).
- `Options(None)` keeps raising `ValueError`; `Options("")` now raises `TypeError` instead of producing zero options.

**D2: Rescue `within_tolerance` coverage with minimal hand-built options.**
Rather than preserving the 52-option fixture list, the rescued tests construct a small set of `Option` tuples that exercise every `within_tolerance` branch:
- range constraint with quant (exact, inexact, and tolerance-parameter cases)
- list constraint and `TYPE_BOOL`/`TYPE_STRING` equality (positive/negative)
- `TYPE_INT`/`TYPE_FIXED` with no constraint (difference vs tolerance)
- constraint-`None` fall-through returning `False`
This keeps the branch coverage while dropping the parser dependency.

**D3: Test reorganization.**
- Rescued `within_tolerance` and constructor-error tests go into `test_scanner_options.py` (its existing list-branch test stays).
- `test_02_scanner_options_from_data.py` → `test_scanner_options_from_data.py`: content unchanged, legacy prefix dropped.
- Parser-fidelity tests (`canon`, `epson1`, `epson_3490`, `epson_gt_2500`, `hp`, `brother`, `snapscan`, `umax`) deleted wholesale, along with all 16 files under `scantpaper/tests/scanners/`.
- Note: `test_02_scanner_options_fujitsu.py` is deleted too; the `delete_*`/`by_title` coverage it carried disappears with the removed methods.

**D4: Remove the orphaned methods.**
`delete_by_index`, `delete_by_name`, `by_title`, and the `device` attribute have no production callers (verified by grep across `scantpaper/`). Removing them is consistent with the dead-code sweep.

## Risks / Trade-offs

- [Rescued `within_tolerance` tests under-cover a branch] → The test list mirrors the branch map in D2 exactly; run the full suite and diff coverage against the current run to confirm no regression.
- [A latent production caller of a removed method surfaces post-change] → Grep for `delete_by_index|delete_by_name|by_title|_parse_scanimage_output` across `scantpaper/` after removal; CI's `pytest` + `pylint` catch dangling references.
- [Coverage ratio dips below 98%] → Removing covered-dead-code removes roughly equal statements from both numerator and denominator; verify with a full `pytest` run and add targeted tests only if the ratio drops.

## Migration Plan

Internal-only refactor; no user-facing migration. Rollback is `git revert` of the change commit.

## Open Questions

None — the `test_02_scanner_options_from_data.py` rename is a pure file move with no behavior change.
