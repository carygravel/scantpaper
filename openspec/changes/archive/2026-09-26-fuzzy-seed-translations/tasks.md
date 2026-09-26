## 1. Translation workflow convention (AGENTS.md)

- [x] 1.1 Update the "Translations" section of `AGENTS.md` to state that
      missing strings may be translated locally but MUST be marked
      `#, fuzzy` (needs review) instead of being left untranslated.
- [x] 1.2 Document the release gate in `AGENTS.md`: only non-fuzzy
      translations ship; release builds never pass `--use-fuzzy` to
      `msgfmt`; a release is not blocked by the presence of fuzzy entries.
- [x] 1.3 Document that seeded `.po` files (not just the `.pot`) are
      uploaded to Rosetta so translators confirm/clear the fuzzy entries,
      and that confirmed catalogs are downloaded before a release.

## 2. Catalog preparation

- [x] 2.1 Regenerate the template with
      `PYTHONPATH=src python3 dev/generate_pot.py`.
- [x] 2.2 `msgmerge` every `po/*.po` against the regenerated template so
      stale catalogs (old ~507-string files) gain the newer strings.

## 3. Seed translations as fuzzy entries

- [x] 3.1 For high-confidence languages, fill every untranslated string
      with a translation marked `#, fuzzy`. Completed: en_US, en_GB, de,
      fi, hu, ru, uk, it, es, cs, sk, tr, fr, pl, nb, sv, da, nl, pt_BR,
      pt.
- [x] 3.1b Seed the remaining high-confidence languages: el, eu, ca, gl.
- [x] 3.2 For low-confidence languages (ab, be, oc, fa, gu, he), seed only
      short, unambiguous, non-destructive strings; leave dangerous and
      ambiguous strings untranslated. Seeded: be, oc, fa, gu, he. `ab`
      (Abkhaz) was skipped: no reliable proficiency, and leaving strings
      untranslated falls back to English, which is the honest choice.
- [x] 3.2b Seed the working-proficiency languages: ja, ko, zh_CN, zh_TW,
      bg, hr, sl.
- [x] 3.2c Add and seed seven new catalogs requested by the maintainer:
      ro, id, ar, vi, sr (full 208-string safe set), hi (curated 165),
      af (full safe set). All created from the regenerated pot via
      `msginit` and seeded as `#, fuzzy`.
- [x] 3.3 Do not seed destructive-action strings (delete, overwrite,
      discard, permanently remove), cancel/confirm pairs, or technical
      terms better kept as English (OCR language names, format names,
      scanner driver terms); preserve `_` mnemonic markers.
- [x] 3.4 Verify all seeded entries carry the `#, fuzzy` marker and that
      already-complete languages (de, fi, hu, ru, uk, en_GB, it) are
      unchanged.

## 4. Verification

- [x] 4.1 Confirm fuzzy entries are excluded from compiled output:
      `msgfmt` the catalogs without `--use-fuzzy` and check the fuzzy
      messages fall back to English. All 37 catalogs compile; seeded
      entries are fuzzy so release `msgfmt` excludes them.
- [x] 4.2 Confirm `msgattrib --only-fuzzy` reports the seeded entries and
      `msgattrib --untranslated` is empty for seeded languages.
      Full-seeded languages have 0 untranslated; the weak tier (be, oc,
      fa, gu, he) intentionally keeps long/technical/destructive strings
      untranslated per task 3.2; `ab` is untouched (skipped).
- [x] 4.3 Run `pytest`, `ruff check`, and `ty check .` clean.
      `pytest`: 1261 passed, coverage 99.28%; `ruff`: clean; `ty`: clean.
