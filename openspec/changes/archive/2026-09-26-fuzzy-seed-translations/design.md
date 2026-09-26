## Context

See proposal.md - Why for motivation. Current state: `po/*.po` files carry
gaps from a few dozen to entire stubs; several files (ja, ko, pt, nb, sv,
zh_CN, gu, he, ...) are at an old 507-string template count and are missing
~117 newer strings entirely. `AGENTS.md` currently forbids local edits to
`.po` files. All files have zero fuzzy entries today, so the fuzzy flag is
free to adopt. Translations are processed via Rosetta (Launchpad); gettext
falls back to the English `msgid` for untranslated or fuzzy strings.

## Goals / Non-Goals

**Goals:**
- Turn untranslated strings into fuzzy-marked seed material that human
  translators confirm through the existing Rosetta flow.
- Guarantee fuzzy strings are never visible to end users.
- Bring stale `.po` files up to the current template.

**Non-Goals:**
- No runtime code changes; no change to `dev/generate_pot.py`.
- No change to how Rosetta downloads/clears translations.
- No requirement that all fuzzy strings be cleared before a release.

## Decisions

### D1: Use `#, fuzzy` as the seed marker
Each machine-filled translation gets a `#, fuzzy` comment line. This is
the gettext-native "needs review" flag, honored per-string, and Rosetta
presents fuzzy entries to translators as needing confirmation.

- Alternative: whole-file header comment — too coarse to track per-string
  progress.
- Alternative: separate `-machine.po` catalogs merged at build — cleaner
  provenance but adds build plumbing for no user-visible gain, and Rosetta
  cannot consume them as naturally.

### D2: Release gate is "only non-fuzzy strings ship", via default gettext
The gate is the gettext default: fuzzy entries are excluded from compiled
catalogs unless `--use-fuzzy` is passed. So the rule is simply that release
builds never pass `--use-fuzzy`; fuzzy entries automatically fall back to
English and do not block a release.

- Alternative considered (rejected): block releases while any fuzzy entry
  remains. This stalls releases on translator availability and contradicts
  the goal of shipping whatever has been confirmed.

### D3: Re-merge stale catalogs before seeding
Run `msgmerge` (via the regenerated `scantpaper.pot`) on every `.po`
before filling gaps, so the old-507 files gain the newer strings. Without
this, seeding would fill gaps in an outdated template and miss ~117
strings per stale language.

### D4: Tiered seeding by confidence
Seed languages in three waves:
1. **Full seed** — languages where translation quality is high (fr, nl,
   sv, el, pl, cs, sk, tr, es, eu, da, ...): every gap filled and marked
   fuzzy.
2. **Simple-strings only** — weak languages (ab, be, oc, fa, gu, he):
   seed only short, unambiguous, non-destructive strings; leave dangerous
   or ambiguous ones untranslated.
3. **Skip** — languages that are complete already.

Rationale: the human gate catches errors, but a subtly wrong seed in a weak
language is more likely to be rubber-stamped than corrected, and is more
confusing to a translator than a blank string. Erring toward "leave blank"
in weak languages keeps the seed trustworthy where it matters.

### D5: Dangerous/technical strings stay untranslated
Never machine-seed strings whose mistranslation is harmful or meaningless:
destructive actions (delete, overwrite, discard, permanently remove),
cancel/confirm pairs, and technical terms best kept as English loanwords
(OCR language names, format names, scanner driver terms). Also preserve
`_` keyboard mnemonic markers when translating.

### D6: Convention change in AGENTS.md
Rewrite the translation workflow section: missing strings may be translated
locally but MUST be marked `#, fuzzy`; upload the seeded `.po` files (not
just the `.pot`) to Rosetta; before release, download cleared translations;
release builds never use `--use-fuzzy`.

## Risks / Trade-offs

- **Rubber-stamping** → tiered seeding (D4) keeps the seed quality high
  where translators are most likely to confirm without editing; dangerous
  strings are never seeded (D5).
- **Human translators over-trust fuzzy entries** → fuzzy is Rosetta's
  native "needs review" state; translators are accustomed to treating it
  as provisional, unlike finished-looking strings.
- **Seed drift** — if the `.pot` grows before translators clear flags, new
  strings simply stay untranslated (fall back to English) with no harm.
- **Fuzzy flag accidentally stripped** → any step that merges or edits the
  `.po` must preserve `#, fuzzy` markers; verified with
  `msgattrib --only-fuzzy` before upload.
