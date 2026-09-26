## 1. Pot generation with format flags

- [x] 1.1 Switch `dev/generate_pot.py` from `pygettext3` to `xgettext`
      (`xgettext --language=Python`), keeping the `intltool-extract` step
      for `.ui` files; pass `--flag=_` (python-format) and
      `--flag=_:python-brace-format` so format flags are emitted.
- [x] 1.2 Regenerate `scantpaper.pot` and verify it now carries
      `#, python-format` flags on `%`-format strings.

## 2. Deterministic catalog checker

- [x] 2.1 Add `dev/check_po.py`: for each `po/*.po` run
      `msgfmt --check -o /dev/null` via subprocess and validate the
      `Plural-Forms` header against an embedded CLDR table keyed by
      language code (nplurals=3 for ru/uk/pl/be/sr/cs/sk, 4 for sl, 6 for
      ar, etc.); print a per-file report and exit non-zero on any failure.
- [x] 2.2 Run `msgmerge` on every `po/*.po` against the regenerated pot so
      catalogs gain the format flags, then run `dev/check_po.py` and
      resolve every reported finding (fixing either the source string or
      the catalog, never disabling the check).

## 3. CI enforcement

- [x] 3.1 Add `test_check_po_files()` to
      `src/scantpaper/tests/test_po_files.py` that invokes
      `dev/check_po.py` and asserts rc==0, mirroring the existing
      `test_compile_po_files` test.
- [x] 3.2 Add `gettext` to the `apt-get install` dependency lists in
      `.github/workflows/test.yml` (all jobs that run pytest) so `msgfmt`
      is guaranteed present.

## 4. Documentation

- [x] 4.1 Update the AGENTS.md Translations section to state that catalogs
      must pass `dev/check_po.py`, that counted strings use `ngettext`
      (never `_()`), and that new languages must set a CLDR-correct
      `Plural-Forms` header.
