# Tasks: Restructure translation catalogs for Launchpad Rosetta

## 1. Move the catalogs

- [x] 1.1 Move the 44 catalogs from `po/scantpaper-<lang>.po` to
  `po/scantpaper/<lang>.po` with `git mv`
- [x] 1.2 Confirm `po/TRANSLATION-FINDINGS.md` remains at `po/` (not moved)

## 2. Default pot path

- [x] 2.1 Add an `--output` option to `dev/generate_pot.py`, defaulting to
  `po/scantpaper/scantpaper.pot` resolved against the repo root, creating
  parent directories
- [x] 2.2 Update `.gitignore` so the pot is ignored at its new path

## 3. Update the tooling

- [x] 3.1 `dev/check_po.py`: default `--src` to `po/scantpaper`, derive the
  language from the filename stem, and pass `--output <tmp>/scantpaper.pot`
  when generating the template into its temporary directory
- [x] 3.2 `dev/compile_mo.py`: default `--src` to `po/scantpaper`, derive the
  domain from the template directory name and the language from the stem,
  keeping `--domain` as an override
- [x] 3.3 `dev/summarise_po.py`: default `--src` to `po/scantpaper` and derive
  the language from the filename stem

## 4. Tests, docs and tarball

- [x] 4.1 Update `src/scantpaper/tests/test_po_files.py`: point the
  real-catalog tests at `po/scantpaper`, build synthetic catalogs under
  `<tmp>/po/scantpaper/`, and pass `--output <tmp>/scantpaper.pot` in the
  generation tests
- [x] 4.2 Update `README.md` and `AGENTS.md` paths and the `generate_pot.py` /
  `compile_mo.py` usage to the new layout
- [x] 4.3 Add `dev/rosetta_tarball.py` (or documented command) that wraps
  `po/scantpaper/` into the Rosetta upload archive

## 5. Verification

- [x] 5.1 Regenerate the pot at the new default path and confirm
  `python3 dev/check_po.py` reports 44 catalogs and 0 errors
- [x] 5.2 `python3 -m pytest` passes with coverage not below 99.28%, and
  `ruff check`, `ruff format --check` and `ty check .` are clean
- [x] 5.3 Confirm no `scantpaper-<lang>.po` files remain and the tree holds no
  stray `scantpaper.pot` outside `po/scantpaper/`
