## 1. Script scaffolding

- [x] 1.1 Create `dev/release.py` with an `argparse` CLI: `--version`,
  `--date`, `--dry-run`, and `--root` (default: repo root), matching the style
  of `dev/generate_pot.py`
- [x] 1.2 Define the pure helper signatures (`resolve_version`,
  `resolve_date`, `stamp_changelog`, `bump_pyproject`, `add_metainfo_release`)
  as `str -> str` transforms with no file I/O

## 2. Tests (write first)

- [x] 2.1 Add `src/scantpaper/tests/test_release.py` following the
  `test_po_files.py` subprocess-on-a-fixture-tree pattern
- [x] 2.2 Test version resolution: heading-only, `--version` matching,
  `--version` mismatch, and no `(unreleased)` heading
- [x] 2.3 Test date resolution: shared date in changelog and metainfo,
  `--date` override, and `SOURCE_DATE_EPOCH`
- [x] 2.4 Test `stamp_changelog`: `(unreleased)` becomes the date and bullets
  are unchanged
- [x] 2.5 Test `bump_pyproject`: version changes and all other lines are
  byte-identical
- [x] 2.6 Test `add_metainfo_release`: new entry is first under `<releases>`,
  older entries unchanged, header comment preserved
- [x] 2.7 Test all-or-nothing: an unparsable metainfo file leaves all three
  files untouched and exits non-zero
- [x] 2.8 Test `--dry-run`: reports changes, writes nothing

## 3. Implementation

- [x] 3.1 Implement `resolve_version` (single `(unreleased)` match; optional
  matching `--version`) and `resolve_date` (`--date` > `SOURCE_DATE_EPOCH` UTC
  > local date)
- [x] 3.2 Implement `stamp_changelog`, `bump_pyproject`,
  `add_metainfo_release` using narrow, anchored edits
- [x] 3.3 Implement orchestration: validate all three transforms in memory,
  then write; support `--dry-run` and print a summary/diff
- [x] 3.4 Verify transformations on the real files without writing
  (`--dry-run`)

## 4. Documentation

- [x] 4.1 Update `release_procedure.md`: replace the manual pyproject and
  metainfo version steps with running `dev/release.py`, and note it also stamps
  the changelog date
- [x] 4.2 Confirm `README.md` needs no change (developer-only tooling)

## 5. Verification

- [x] 5.1 Run `pytest` and confirm all tests pass and coverage does not regress
- [x] 5.2 Run `ruff format` and `ruff check`
- [x] 5.3 Run `ty check .` and confirm no diagnostics
- [x] 5.4 Run `openspec validate automate-release-script --strict`
