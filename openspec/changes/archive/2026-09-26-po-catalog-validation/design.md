## Context

`generate_pot.py` currently uses `pygettext3` (Python's legacy extractor),
which emits no `#, python-format` flags, so `msgfmt --check-format` has
nothing to validate. The translation catalogs are committed to the repo and
compiled in CI via `dev/compile_mo.py` (polib) through
`test_po_files.py`, but that path performs no format/plural/escaping checks.
See proposal.md for motivation; the `translations` spec states the required
behaviour.

## Goals / Non-Goals

**Goals:**
- Give `msgfmt --check` real signal by making the pot carry format flags.
- Add a deterministic, dependency-free catalog checker covering the three
  named problem classes: placeholder/format drift, plural-form headers,
  escaping.
- Enforce it in CI so a bad catalog fails the build on every push.
- Keep the checker outside the coverage-measured package.

**Non-Goals:**
- Catching wrong-but-well-formed translations (semantics stay with Rosetta
  humans and any future model review).
- Adding third-party linters (`msgcheck`, Translate Toolkit) as new
  dependencies.
- Reformatting/rewriting existing catalog translations.

## Decisions

**D1: Switch the pot generator from `pygettext3` to `xgettext`.**
`xgettext --language=Python` auto-detects `%`-format strings and marks them
`#, python-format`; `--flag=_:python-brace-format` covers `.format()`
strings if used. This is the root-cause fix that makes `msgfmt
--check-format` meaningful. `pygettext3` was chosen originally for its
simple invocation, but it cannot emit the flags the check depends on.
Alternative considered: post-process the pot to inject flags — rejected as
brittle; xgettext is the supported tool. Note: `xgettext` must also handle
the `.ui` files (currently via `intltool-extract`) — keep that step and
pass the resulting `.h` sources to xgettext.

**D2: New `dev/check_po.py` runs `msgfmt --check` + CLDR header check.**
For each `po/*.po`, run `msgfmt --check -o /dev/null` via subprocess and
validate the `Plural-Forms` header against a small embedded CLDR table keyed
by language code (ru/uk/pl/be/sr/cs/sk → nplurals=3, sl → 4, ar → 6,
etc.). Exit non-zero with a per-file report. Placing it in `dev/` (not a
package) keeps it out of the coverage-measured tree, mirroring
`compile_mo.py`. Alternative considered: extend `test_po_files.py` directly
with the checks — rejected because the CLDR logic would then sit in the
coverage-measured package.

**D3: Enforce via the existing pytest suite, not a new workflow.**
Add `test_check_po_files()` to `src/scantpaper/tests/test_po_files.py`
that invokes `dev/check_po.py` and asserts rc==0, matching the existing
compile test. pytest already runs in every `test.yml` job, so the gate is
uniform. Also add `gettext` to the `apt-get install` lines so `msgfmt` is
guaranteed present.

**D4: AGENTS.md documents the rule; CI enforces it.**
The AGENTS.md Translations section gains a short validation bullet (run the
checks; counts use `ngettext`; new languages set a CLDR-correct
`Plural-Forms` header). AGENTS is guidance for humans/agents; CI is the
hard gate. The two are complementary, not alternatives.

## Risks / Trade-offs

- **Large pot diff on regeneration** (every catalog gains format flags
  after `msgmerge`) → expected one-time churn; the check then prevents
  regressions.
- **`xgettext` may flag existing strings differently** (e.g. a literal `%`
  that is not a real format) → treat check failures as findings to fix in
  the source or the catalog, not as reason to disable the check.
- **msgfmt only checks entries carrying format flags** → the whole point of
  D1; until the pot is regenerated, the check under-reports, so the pot
  switch must land with the check.
- **CLDR table needs maintenance as languages are added** → keep it small
  and explicit; add a row whenever a new catalog is created.
