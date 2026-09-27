## Context

`dev/check_po.py` already separates hard failures from advisory output: the
`errors` list drives the exit code, and `_hygiene()` returns `advisory_lines`
that are printed but do not fail. The new checks should extend those two
existing channels rather than introduce a third severity level.

Two measurements shape the design:

- Every one of the 48 wrong English strings fixed during review had a `msgstr`
  that was **verbatim a different msgid in the same catalog** (`Select Odd` ==
  `Selected`, `Cut` == `Cu_t`, `Rotate 180°` == `Rotate`). That is a single
  high-signal signature.
- Applying that signature to the 44 current catalogs yields 25 hits, of which
  16 are the same defect recurring: `_Ok` and `_OK` are *both* msgids, so a
  correct translation of one coincides with the other. Without a principled
  discriminator the check is unusable, and `AGENTS.md` forbids suppressing a
  check to make a catalog pass.

Current source-side defects measured across the 551 active msgids: one `(s)`
hack, four case-only-duplicate pairs, five concatenation fragments, one
doubled space, one Greek-mu msgid, four msgids over 200 characters.

## Goals / Non-Goals

**Goals:**

- Make the one mechanically-unambiguous, authorable defect class — embedded
  plural hacks — impossible to merge.
- Convert the manual detection that produced `po/TRANSLATION-FINDINGS.md` into
  a repeatable check, so the backlog cannot regrow unnoticed.
- Leave the advisory output actionable: every reported string should be one a
  native speaker can fix.

**Non-Goals:**

- Automatically authoring any translation. Every advisory identifies a string;
  a human supplies the wording.
- Fixing only the *unambiguous* source msgid defects the advisories report
  (`_Ok`/`_OK`, `PPI`/`ppi`, the doubled space). These are one-line edits, and
  they are done in this change so the new checks start green rather than firing
  on defects already known.
- Restructuring the five concatenation fragments. Two of them concatenate a
  translated sentence directly with a non-translated list, e.g.
  `_("...too big to be scanned by the selected device:") + " " +
  ", ".join(self.ignored_paper_sizes)`, which fixes English word order and an
  ASCII separator into a translatable string. That is a code change needing its
  own decision on interpolation, not a string edit.
- Choosing an encoding for `μs`. SI specifies U+03BC, which is what the tree
  already uses, while most software uses U+00B5. The condition therefore stays a
  standing warning rather than becoming a defect to fix.
- Re-merging the 44 catalogs. See "Catalog re-merge" below.

## Decisions

### The hard-fail rule matches a bare plural suffix only

The check fires on `\w\((?:s|es)\)` — a word character immediately followed by
a parenthesised `s` or `es`.

Alternatives considered and rejected:

- *Any `\(s\)` anywhere.* Simpler, but also fires on `(s)` used as prose
  ("choose the format(s) below"), which is the same author error and so still
  correct — however it cannot be extended to other languages' suffixes without
  becoming unbounded.
- *Any parenthesised lowercase token*, to generalise to `(es)`. Rejected: it
  would fire on legitimate constructs already in the tree, such as
  `Use LibTIFF (tiff2ps)` and `Device blacklist (regular expression)`, and
  those are the cases the spec explicitly exempts.
- *Detecting a plural of the preceding word by morphology.* Requires
  per-language inflection, which is not implementable as a check.

Fixing `(s)` means `ngettext()` for genuinely counted text, or rewording. The
spec wording tells the author which.

### `Open image file(s)` becomes `Open images`

`Open images` uses a generic plural noun, which every target language can
express, and the button already carries the standard Open icon, so `file` is
redundant in a tooltip.

Rejected: `Open image files` (keeps a plural noun that still needs agreement,
for no gain over `images`); `Open an image` (singular is safest but reads as
single-file when the chooser is multi-select); `Choose images to open`
(needlessly verbose for a tooltip).

### The mistranslation check suppresses self-variants by rule, not by allowlist

For condition (e), normalise both the entry's `msgid` and every catalog
`msgid` by lowercasing and removing `_`, then report when the `msgstr`
normalises to a *different* msgid's normalisation. Crucially, a match is
suppressed when the `msgstr` also normalises to its **own** msgid — which is
exactly the `_Ok` / `_OK` case, where the difference from the entry's own
source is case only.

This is a discriminator derived from the data, not an exemption list, so it
needs no `AGENTS.md` exception and cannot rot as msgids are added. It reduces
25 raw hits to the ~8 that are genuine: `it` `hOCR` == `_OCR`, `fr` ×4
including `Joint Photographic Experts Group JFIF format` == `JPEG`, `nl` ×2,
`ca`/`hu` `Tagged Image File Format` == `TIFF`.

### The source msgid set is generated per run into a temporary directory

`check_po.py` invokes the existing generator once, into a
`tempfile.TemporaryDirectory()`, and reads the msgid set from there. The POT
stays untracked and is added to `.gitignore`.

Alternatives considered:

- *Commit the POT.* Rejected: it is a build artifact, and a stale committed copy
  is indistinguishable from a current one.
- *Derive the msgid universe from the union of the 44 catalogs.* Rejected: it
  cannot see a msgid that exists in source but has never been merged into any
  catalog — precisely the new-string case these checks exist to catch — and it
  inherits obsolete drift.

Consequence accepted: checking now requires `xgettext`/`msgcat` on `PATH`. CI
already installs `gettext`. If generation fails, the checker must fail loudly
rather than skip, otherwise the source-side checks would vanish silently on
any machine without gettext.

### Accelerator conditions were measured and rejected

The change originally specified two accelerator conditions: a declared
accelerator the translation drops, and one whose letter differs from the
English msgid. Measured against the 44 catalogs, the letter condition
reported **558** entries that were all correct translations -- `_File` ->
`_Datei`, `_Save` -> `_Guardar`, `_Delete` -> `_Выдаліць`, and the CJK
`放大(_I)` convention. A mnemonic has to point at a character that exists in
the *translated* word, so demanding the English letter is unsatisfiable for
most languages.

The presence condition reported 315 entries, but that count depended entirely
on a heuristic for what counts as a mnemonic in a non-Latin script, and the
project has no reliable way to adjudicate the remainder. Neither condition
yields something a maintainer can act on correctly, so both are dropped rather
than shipped as noise. The underlying observation is kept in the spec so the
idea is not re-proposed without the measurement.

### Source-wide checks run once, not per catalog

Conditions (i)–(m) are properties of the msgid set, so they are evaluated once
and reported once. Re-reporting them 44 times would bury the per-catalog
findings that a reviewer actually has to act on.

### Catalog re-merge is deferred, and the coupling is documented

The `%` change already left a stale msgid in every catalog, and this change
removes three more (`Open image file(s)`, `_Ok`, `PPI`). Absorbing them
requires an `msgmerge` over 44 catalogs, which turns four msgids obsolete
everywhere. Measured across the catalogs, all 44 hold all four as live entries,
so the merge pushes 35 ceilings in `OBSOLETE_CEILING` over by four — they are
currently pinned to exactly each language's present count.

Worse, nine catalogs have no ceiling at all (`ab`, `af`, `ar`, `en_US`, `hi`,
`id`, `ro`, `sr`, `vi`), so they fail on *any* obsolete entry and need a
ceiling value added rather than raised. The merge and the ceiling work are
therefore one coupled unit covering both effects.

This change deliberately performs only the source rewords and leaves the
catalogs stale. Nothing breaks in the interim: the hard check reads the
on-the-fly POT, not the catalogs, and a stale msgid still translates to
`%` / its old text harmlessly. The trade-off is a known temporary divergence
between source and catalogs, recorded in `tasks.md` so the next merge is done
with the ceiling work rather than discovering 44 failures at once.

## Risks / Trade-offs

- **Advisory noise.** The catalog-side conditions report 20 entries across the
  44 catalogs -- 6 for (e) and 14 for (f) -- and the source-side conditions
  report 15. All were inspected by hand and are real, but the maintainer is
  not a reliable judge of translation quality, so an advisory they cannot
  resolve is a report they will learn to ignore. -> The source-side conditions
  are the ones that pay off here, because every one is a defect in an English
  string or in code structure, which is entirely within the maintainer's
  authority. The catalog-side conditions are retained as *detection* only, and
  are worth little unless their output is routed to native speakers; that
  routing is not part of this change and is recorded as a follow-up.
- **Check requires gettext at check time**, so a contributor without it sees a
  hard failure rather than a skipped check. → Deliberate; a silently absent
  check is worse than a loud one, and the error message will name the missing
  tool.
- **Advisories never block**, so a mistranslation can ship if every reviewer
  ignores them. → Accepted: the alternative is failing the build on strings only
  a native can fix, which invites a wrong "fix". The obsolete ceiling already
  provides the hard ratchet; these conditions are review prompts.
- **Doubling the reported count is not possible today** — the msgid is being
  removed in the same change — so the new hard check starts green. If a future
  change reintroduces a `(s)` msgid, CI fails at once.
