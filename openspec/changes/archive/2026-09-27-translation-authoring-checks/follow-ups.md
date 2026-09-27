# Follow-ups from translation-authoring-checks

These are **not** tasks of the `translation-authoring-checks` change. They are
recorded here so the reasoning and the measurements survive, and so nothing is
silently dropped. Each item is a candidate for its own change proposal.

## 1. Catalog re-merge, and the ceiling work coupled to it

The change removes four msgids from the source: `%` (an earlier un-merged
change), `Open image file(s)`, `_Ok` (now `_OK`) and `PPI` (now `ppi`). All 44
catalogs still hold all four as live entries, so the next `msgmerge` turns
four msgids obsolete in every catalog.

What a msgid change actually costs, measured on `scantpaper-de.po` by merging
the current source into the pre-change catalog:

- Obsolete entries went 138 → 142, i.e. **+2 for the two msgids this change
  altered**. The old translation is *not* lost: `msgmerge` fuzzy-matches the
  new msgid against the old one and carries the `msgstr` over marked `#, fuzzy`.
- Fuzzy entries went 0 → 2, the same two strings. A fuzzy entry falls back to
  English in a release build, since releases never pass `--use-fuzzy`.

So only the changed string is affected, not the other ~1,270 in the catalog.
The expensive part is the obsolete count, because `OBSOLETE_CEILING` is pinned
to each language's exact present total.

- [ ] Re-merge all 44 catalogs to absorb the four stale msgids. **Must be done
      together with the two items below**, because `OBSOLETE_CEILING` in
      `dev/check_po.py` is pinned to exactly each language's present obsolete
      count, so the merge alone fails 35 ceilings.
- [ ] Raise all 35 values in `OBSOLETE_CEILING` by **4**, the number of msgids
      this change and the earlier un-merged one removed. Re-derive it from the
      merged catalogs rather than trusting this number.
- [ ] Add a ceiling for the nine catalogs that have none: `ab`, `af`, `ar`,
      `en_US`, `hi`, `id`, `ro`, `sr`, `vi`. These fail on *any* obsolete
      entry, so the merge breaks them outright and they need a value *added*
      rather than raised. Consider whether `en_US` wants one at all, given it
      is the reference catalog.
- [ ] Clear the 4 new fuzzy entries per catalog, so the four strings ship
      translated again rather than falling back to English.

Note that `_Ok` → `_OK` and `PPI` → `ppi` each obsolete an entry rather than
renaming it in place, because the target msgid already exists alongside the one
being removed.

The doubled space in `src/scantpaper/savethread.py:291` is a fifth such msgid
edit, deliberately not made, so that the msgid stays stable while this work is
sequenced. Removing it would add a sixth obsolete and fuzzy entry per catalog,
so it belongs in the same re-merge, not before it.

## 2. The five concatenation fragments

`dev/check_po.py` reports these as condition (j). All five have a mechanical
fix requiring no judgement about any language:

- `src/scantpaper/dialog/sane.py` — three `Error ...: ` prefixes concatenated
  with a SANE status string. These are **user-facing**: they reach
  `_show_message_dialog(text=msg)` at `src/scantpaper/app_window.py:904`, so
  they must stay translatable. Interpolate instead, e.g.
  `_("Error opening device: %(status)s") % {"status": response.status}`.
- `src/scantpaper/dialog/scan.py:1069` and
  `src/scantpaper/dialog/preferences.py:397` — a translated sentence
  concatenated with a non-translated list (`+ ", ".join(...)`), which fixes
  both English word order and an ASCII separator into a translatable string.

Doing this takes condition (j) from 5 to 0.

## 3. Routing the catalog-side advisories to native speakers

Conditions (e) and (f) detect mechanically but cannot be corrected by the
maintainer, who is not a reliable judge of translation quality. An advisory
that cannot be acted on is one that gets ignored, so the output needs to reach
the people who can fix it. Candidates, none decided:

- Mark (e)/(f) findings `#, fuzzy`. `msgfmt` excludes fuzzy entries, so the
  wrong string stops shipping and the English msgid is shown instead, and
  Rosetta presents fuzzy entries to translators as needing translation. This
  fits the existing policy in `AGENTS.md`, where fuzzy means "needs human
  review". Cost: roughly 20 strings show English until a native speaker
  picks them up, which for `Select Odd` / `Select Even` is better than a
  translation that conflates two controls.
- Emit a per-language report that can be filed as a Launchpad bug against that
  locale's translators. Purely mechanical work for the maintainer: no
  translation judgement, just filing precise reports.

## 4. Ratchet down the obsolete backlog

3,037 obsolete entries are currently in the catalogs, and they are the surface
`msgmerge` fuzzy-matches new msgids against. The bad bindings catalogued in
`po/TRANSLATION-FINDINGS.md` — `Select Odd` bound to `Selected`, `Cut` bound
to `Cu_t` — are a mechanical consequence of that backlog, not bad luck. Purging
needs no language skill, needs no new tooling, and the ceiling machinery
already exists. Lower `OBSOLETE_CEILING` values as each language is purged.

## 5. The `μs` encoding

SI specifies U+03BC GREEK SMALL LETTER MU, which is what the tree already
uses, while most software uses U+00B5 MICRO SIGN. Condition (l) is therefore
a standing warning rather than a defect to fix. Deciding it would let (l) either
become a hard check or be dropped.

## 6. Accelerator conditions: measured and rejected

Do not re-propose these without repeating the measurement. Against the 44
catalogs:

- Requiring the accelerator letter to match the msgid flagged **558** entries,
  all of them correct translations: `_File` → `_Datei`, `_Save` → `_Guardar`,
  `_Delete` → `_Выдаліць`, and the CJK `放大(_I)` convention. A mnemonic has to
  point at a character that exists in the *translated* word, so the condition
  is unsatisfiable for most languages.
- Treating an absent marker as a defect produced **315** entries, a count that
  depended entirely on a heuristic for what counts as a mnemonic in a
  non-Latin script, with no reliable way to adjudicate the remainder.

## 7. Standing advisories that are correct to keep

Not every advisory finding is a defect. After the fixes in this change, the
checker reports two conditions that will keep firing by design:

- Condition (i) reports 2: `Scan Options`/`Scan options` and
  `Scan Document`/`Scan document`. Each pair is a title-cased window title and
  a sentence-cased button label, which are genuinely different strings. The
  check is still worth keeping, because the same condition did catch the
  real defects `_Ok`/`_OK` and `PPI`/`ppi`, but these two need ignoring.
- Condition (l) reports 1, the `μs` in the microsecond time unit, pending the
  encoding decision in section 5.

## 8. Language-independent catalog checks, if ever wanted

Checks that need no language knowledge, and so *can* be trusted by a maintainer
who does not read the target language: a long `msgstr` identical to its
`msgid` means untranslated, and terminal-punctuation or whitespace drift from
the msgid is a formatting defect. Lower value than items 1–4, and more
heuristics to rot.
