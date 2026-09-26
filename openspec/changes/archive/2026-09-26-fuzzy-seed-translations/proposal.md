## Why

Many of the `po/*.po` files shipped with scantpaper are incomplete: some
languages have a few dozen missing strings, others (Abkhaz, Belarusian,
Occitan, Persian) are essentially empty stubs. Today those strings fall
back to English, which is useless to speakers who do not read English.
Machine-generated translations, marked as needing review, give human
translators a starting point to confirm or fix instead of translating from
scratch — and a poor-but-reviewable translation is better than no
translation for a non-English speaker.

## What Changes

- Update `AGENTS.md` so the translation workflow explicitly allows
  translating missing strings and marking them `#, fuzzy` (needs review)
  instead of leaving them untranslated. This replaces the current rule that
  forbids adding translations locally.
- Seed the `po/*.po` files that have gaps with machine-generated
  translations, each marked `#, fuzzy`. Fuzzy strings are invisible to end
  users (gettext falls back to English) until a translator confirms them.
- Define the release gate: **only non-fuzzy strings ship**. Fuzzy entries
  are never used in a release build; a release is not blocked by the
  presence of fuzzy strings. Translators clear the fuzzy flag over time via
  the existing Rosetta workflow.
- Keep the existing Rosetta (Launchpad) flow unchanged for downloading and
  clearing translations; seeding only changes what is uploaded.

## Capabilities

### New Capabilities
- `translations`: defines how translations are produced, marked, and
  shipped. Fuzzy-marked translations are treated as untranslated (fall back
  to the English `msgid`); only non-fuzzy translations are included in a
  release.

### Modified Capabilities
<!-- None: no existing spec covers the translation workflow. -->

## Impact

- `AGENTS.md` — contribution convention for translations changes.
- `po/*.po` — gap-filling fuzzy entries added across languages; files are
  re-merged against the current `scantpaper.pot` where stale.
- `dev/generate_pot.py` — unchanged (template regeneration is untouched).
- Release/build process — must not use `--use-fuzzy` when compiling
  catalogs, so fuzzy strings never reach users.
- No runtime code, dependencies, or user-visible behavior changes beyond
  the slow arrival of confirmed translations.
