## Why

A msgid can be badly authored and the only symptom appears much later, in a
language nobody on the project reads. Two concrete cases already in the tree:

- `Open image file(s)` embeds an English-only plural hack. A translator cannot
  fix it with `ngettext` (it is not a counted string) and there is no natural
  equivalent in languages with richer plural morphology, so it silently ships
  broken.
- `msgmerge`'s fuzzy matching has repeatedly bound a msgid to a *different*
  real string, producing confident nonsense such as `Select Odd` == `Selected`,
  `Cut` == `Cu_t` and `Invert selection` == `Cut selection`. These are exactly
  the defects catalogued by hand in `po/TRANSLATION-FINDINGS.md`.

Both are mechanically detectable. Neither is currently checked, so the same
mistake recurs. The maintainer has now reviewed 17 locales by hand; automating
the detection is what stops the backlog regrowing.

## What Changes

- Add a **hard-fail** source check rejecting any msgid that embeds a
  parenthesised plural suffix (`(s)`, `(es)`) directly after a word. Counted
  text must use `ngettext()`; other strings must be reworded so no plural
  marker is needed.
- Add **advisory** checks, which report but never fail the build, in two
  families:
  - *Source-side*, over the msgid universe: case-only-duplicate msgids,
    translatable concatenation fragments, double spaces, Greek-mu vs
    micro-sign confusables, and over-long msgids.
  - *Catalog-side*, per catalog: a `msgstr` equal to a **different** msgid in
    the same catalog (the bad-merge signature), sibling strings that must
    differ but are identical, a declared keyboard accelerator dropped by the
    translation, and a changed accelerator letter.
- Build `scantpaper.pot` **on the fly** into a temporary directory so the
  source-side checks have an authoritative msgid set, and keep the POT
  untracked (adding it to `.gitignore`).
- Reword `Open image file(s)` to `Open images` so the new hard check passes.
- Fix the source msgid defects that the new advisories would otherwise report
  from day one, so the checks start green: unify the OK-button label on `_OK`,
  unify pixels-per-inch on `ppi`, and drop a doubled space. The five
  concatenation fragments and the `μs` encoding stay warnings — the first
  because two of them concatenate a translated sentence with a non-translated
  list and need their own interpolation decision, the second because SI and
  common practice disagree on the codepoint.
- Add one sentence to `AGENTS.md` requiring new user-visible strings to be
  considered for ease of translation.

Deliberately **not** checked, because they are idiomatic and would only add
noise: trailing-punctuation twins (`Both sides` / `Both sides.`, a
label/tooltip pair in `postprocess_controls.py`), msgids beginning lowercase
(legitimate for units and proper names such as `mm`, `hOCR`, `unpaper`), and
mnemonic/non-mnemonic twins (`_Save` / `Save`).

## Capabilities

### New Capabilities
<!-- None. This change extends the existing `translations` capability. -->

### Modified Capabilities
- `translations`: extends "Catalog hygiene defects are reported" with a new
  set of advisory conditions, and adds a new requirement making untranslatable
  plural-hack msgids a hard validation failure.

## Impact

- `dev/check_po.py` — new hard-fail check plus the advisory families; needs
  the on-the-fly POT to derive the msgid universe.
- `dev/generate_pot.py` — invoked by the checker rather than only by hand.
- `src/scantpaper/app.ui` — tooltip text `Open image file(s)` → `Open images`
  (user-visible).
- `src/scantpaper/session_mixins.py` — OK-button label `_Ok` → `_OK`.
- `src/scantpaper/dialog/save.py` — PPI spin-button label `PPI` → `ppi`, with
  the hardcoded `"PPI"` in `src/scantpaper/tests/test_052_dialog_save.py`
  updated to match.
- `src/scantpaper/savethread.py` — doubled space in the 2 GiB message.
- `scantpaper.pot` — untracked build artifact; four msgids fewer.
- `.gitignore`, `AGENTS.md`, `README.md`,
  `src/scantpaper/tests/test_po_files.py`,
  `openspec/specs/translations/spec.md`.

No new dependencies: `gettext` (`xgettext`, `msgcat`, `msgfmt`) is already a CI
dependency.

### Known coupling to call out

Rewording a msgid makes the old entry obsolete in all 44 catalogs at the next
`msgmerge`. `OBSOLETE_CEILING` in `dev/check_po.py` is currently pinned to
exactly each language's present obsolete count, so that merge would fail every
catalog that has a ceiling until the values are raised. The re-merge and the
ceiling work are therefore a single coupled unit and must not be split.

Four msgids are removed by this change and the earlier un-merged `%` change, and
all 44 catalogs hold all four as live entries, so each of the 35 ceiling values
must rise by exactly **4**: `Open image file(s)` and `_Ok` → `_OK` and
`PPI` → `ppi` from this change, plus `%`. Note that the last two are cases where
the *target* msgid already exists alongside the one being removed, so each
removal obsoletes an entry rather than renaming it in place. Separately, nine
catalogs have no ceiling at all (`ab`, `af`, `ar`, `en_US`, `hi`, `id`, `ro`,
`sr`, `vi`) and fail on any obsolete entry, so they need a value added. The
numbers were measured against the catalogs, not assumed, and should be
re-derived at merge time.
