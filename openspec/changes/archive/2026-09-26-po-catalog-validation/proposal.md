## Why

Translation strings were wrapped in `_()` opportunistically from the start,
so placeholder (`%d`/`%s`/`{}`) drift, plural-form errors (the 3-form
Slavic set, Arabic's 6 forms) and escaping problems can silently reach
users. The existing tooling cannot catch these: `generate_pot.py` uses
`pygettext3`, which emits no `#, python-format` flags, so
`msgfmt --check-format` has nothing to validate against. These are exactly
the classes of error a deterministic CI gate can catch — AGENTS.md alone is
not an enforcement mechanism.

## What Changes

- Switch `dev/generate_pot.py` from `pygettext3` to `xgettext` so the
  regenerated pot (and every `po/*.po` after `msgmerge`) carries `#,
  python-format` flags, making `msgfmt --check-format` meaningful.
- Add `dev/check_po.py`: for every `po/*.po`, run `msgfmt --check`
  (validates format-specifier drift, escaping, and plural-entry counts)
  and validate the catalog's `Plural-Forms` header against the CLDR table
  for its language (e.g. `nplurals=3` for ru/uk/pl/be/sr/cs/sk, `4` for sl,
  `6` for ar). Exit non-zero with a per-file report.
- Add `test_check_po_files()` to `src/scantpaper/tests/test_po_files.py`
  invoking `dev/check_po.py` and asserting success, so the check runs in
  every `test.yml` job on every push.
- Document the rule in AGENTS.md: catalogs must pass the deterministic
  checks, counts use `ngettext` (never `_()`), and new languages must set a
  CLDR-correct `Plural-Forms` header.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `translations`: add a requirement that translation catalogs are
  mechanically validated (format-string consistency, escaping, and a
  CLDR-correct `Plural-Forms` header) and that the check is enforced in CI.

## Impact

- `dev/generate_pot.py`: pot regeneration switches to `xgettext`; the
  regenerated `scantpaper.pot` changes (gains format flags), and all
  `po/*.po` files gain `#, python-format` flags after the next `msgmerge`.
- New `dev/check_po.py` script (not a Python package, not coverage-measured).
- `src/scantpaper/tests/test_po_files.py`: new test function.
- `.github/workflows/test.yml`: `gettext` added to the `apt-get install`
  lines so `msgfmt` is guaranteed present.
- `AGENTS.md`: Translations section gains the validation rule.
- No runtime/behaviour change to the application itself.
