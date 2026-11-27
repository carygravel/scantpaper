# Design

## Context

See `proposal.md` - Why. The strict-mode hooks already live in the root
`conftest.py`; this refactor changes only how the suite describes its
environment requirements. The test suite has two roots,
`src/scantpaper/tests` and `dev/tests`. The shared probes belong in the
first, next to the tests that use them; `dev/tests` has no locale or tool
guards of its own.

`src/scantpaper/tests` is excluded from the wheel but included in the
test-code audit, so a helper module placed there is measured by
`dev/check_test_coverage.py` and must have every line executed.

## Goals / Non-Goals

**Goals:**

- One locale probe, with an explicit locale category.
- One tool probe and one marker per repeated guard.
- Consistent skip reasons.
- No change to which tests skip or how they run.
- Tests that cover both branches of every new helper.

**Non-Goals:**

- Consolidating the CI, Debian and README dependency lists.
- Changing the strict-mode hooks or the canonical-environment text.
- Adding a new environment requirement.
- Changing the deliberate `LC_CTYPE` check in the PDF save test.

## Decisions

### D1: A test-only `scantpaper.tests.environment` module

The module imports `locale`, `shutil`, `PIL.features`, `pytest` and
`scantpaper.dependencies.jbig2_available`. It lives under
`src/scantpaper/tests`, is excluded from the wheel, and is covered by the
test-code audit. `src/scantpaper/conftest.py` already imports
`scantpaper.tests.scan_mocks`, so importing a test helper from the package
conftest is an established pattern.

### D2: `has_locale(name, category=locale.LC_NUMERIC)` and `requires_locale`

The category parameter preserves the difference the old copies had
without keeping the copies. `conftest.py`, `test_helpers.py` and the
`comma_locale` fixture use the default `LC_NUMERIC`. The PDF save test
passes `locale.LC_CTYPE` explicitly because it sets that category before
saving.

`requires_locale` returns a `pytest.MarkDecorator` whose condition is
evaluated when the marker is created, matching the old module-level
`skipif` behaviour.

### D3: `requires_tool(name)`

The marker replaces every `shutil.which(name) is None` guard and
standardizes the reason on `requires <name>`. The old `cjb2` and `qpdf`
messages said "Please install ..."; no test asserts those strings. A
combined guard becomes two stacked markers; pytest reports the first
missing tool. The markers are evaluated at import time, as the old
`skipif` marks were.

### D4: `requires_jbig2` and `requires_pillow_feature`

`jbig2_available()` is already centralized in `scantpaper.dependencies`;
`requires_jbig2()` only wraps it. The two JPEG 2000 guards become
`requires_pillow_feature("jpg_2000", "JPEG 2000")`, keeping the existing
"Pillow built without JPEG 2000 support" reason.

### D5: `DE_LOCALE` centralizes the locale name

`conftest.py`, `test_helpers.py`, `test_1111_save_pdf.py` and
`test_0610_dialog_scan_sane.py` use `DE_LOCALE` instead of the repeated
`"de_DE.utf8"` literal. The fixture still sets `LC_ALL` and `LANG` to
that name.

### D6: Tests cover both branches of each helper

`src/scantpaper/tests/test_environment.py` tests:

- `has_locale` with `C` and a missing locale.
- `requires_locale` with a monkeypatched probe, asserting the mark's
  condition and reason.
- `requires_tool` with `shutil.which` monkeypatched to a path and to
  `None`.
- `has_jbig2` and `requires_jbig2` with `jbig2_available` monkeypatched.
- `has_pillow_feature` and `requires_pillow_feature` with
  `features.check` monkeypatched.

The audit counts every line in the module, so both the true and false
branches execute.

## Risks / Trade-offs

- A test asserts an old skip reason. -> Verify with a search for `match=`
  on tool reasons and run the full suite.
- The helper imports `scantpaper.dependencies` and Pillow, adding import
  cost. -> The suite already imports both; the conftest imports app
  modules.
- The audit requires full branch coverage of the helper. -> The
  `test_environment.py` cases cover both branches.
- The locale category is easy to lose in the consolidation. -> The PDF
  save test passes `LC_CTYPE` explicitly and is the only caller that
  needs it.

## Migration Plan

No data or API migration. The old helpers and guards are removed in the
same change; there is no compatibility shim.
