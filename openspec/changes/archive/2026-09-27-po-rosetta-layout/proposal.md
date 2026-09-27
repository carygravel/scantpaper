# Proposal: Restructure translation catalogs for Launchpad Rosetta

## Why

Launchpad Rosetta expects translation files in a directory-per-template
layout — each `.pot` in its own directory with the per-language `.po` files
beside it — but our catalogs live flat in `po/` as `scantpaper-<lang>.po`
with the template written to the repo root. Uploading to Rosetta today
therefore requires restructuring the tree by hand. We want the source tree,
the translation tooling and the default pot path to match Rosetta's layout
out of the box, so that uploading is a matter of wrapping the template
directory in a tarball.

## What Changes

- **Move the catalogs** from `po/scantpaper-<lang>.po` to
  `po/scantpaper/<lang>.po`, one file per language inside a template
  directory named after the domain.
- **Change the default pot path**: `dev/generate_pot.py` writes the template
  to `po/scantpaper/scantpaper.pot` (resolved against the repo root) instead
  of `scantpaper.pot` in the current directory, and gains an `--output`
  override.
- **Infer the domain from the template directory name** instead of the
  `scantpaper-` filename prefix, and the language from the filename stem.
  This drops the brittle `scantpaper-` prefix parsing.
- **Update the translation tooling**: `dev/check_po.py`,
  `dev/compile_mo.py` and `dev/summarise_po.py` find catalogs under
  `po/scantpaper` and derive language/domain from the new layout.
- **Update tests, `.gitignore`, README and AGENTS.md** to the new paths.
- **Add a tarball helper** (or documented command) that wraps
  `po/scantpaper/` into the exact Rosetta upload archive.

No user-visible behaviour changes; this is a source-tree, tooling and build
reorganisation.

## Capabilities

No spec-level behaviour changes. The translation *behaviour* (fuzzy
gating, Rosetta round-trip, ITS extraction, catalog checks) is unchanged;
only the on-disk location and how tools derive the domain and language from
filenames change. This change therefore opts out of specs
(`skip_specs: true`).

## Impact

- **Source tree**: `po/` directory layout; the gitignored pot location.
- **Tooling**: `dev/generate_pot.py`, `dev/check_po.py`,
  `dev/compile_mo.py`, `dev/summarise_po.py`.
- **Tests**: `src/scantpaper/tests/test_po_files.py` (real-catalog paths
  and the synthetic catalogs it builds).
- **Config/docs**: `.gitignore`, `README.md`, `AGENTS.md`.
- **Build**: a tarball step for Rosetta upload; the compiled-locale wheel
  packaging is out of scope and unchanged.
