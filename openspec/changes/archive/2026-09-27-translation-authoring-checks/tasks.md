## 1. On-the-fly message template for the checker

- [x] 1.1 Add a helper in `dev/check_po.py` that generates the message template
  into a `tempfile.TemporaryDirectory()` via the existing `dev/generate_pot.py`
  path and returns the active msgid set; fail loudly with a message naming the
  missing tool if generation raises
- [x] 1.2 Call the helper once from `main()`, before the per-catalog loop, and
  pass the resulting msgid set down to the source-side checks
- [x] 1.3 Add `scantpaper.pot` to `.gitignore`
- [x] 1.4 Verify `python3 dev/check_po.py` still reports
  `44 catalogs, 0 error(s)` and that generation happens exactly once per run

## 2. Hard-fail check: embedded plural hacks

- [x] 2.1 Add a failing test in
  `src/scantpaper/tests/test_po_files.py` asserting that a msgid
  `"Open image file(s)"` is reported as an error
- [x] 2.2 Add a failing test asserting the exempt cases are not reported:
  `"(Mb)"`, `"(DCT)"`, `"Device blacklist (regular expression)"`, and
  `"Use LibTIFF (tiff2ps) to create Postscript files from TIFF."`
- [x] 2.3 Implement the check on the generated msgid set using
  `\w\((?:s|es)\)`, emitting an error that names the msgid and points at
  `ngettext()` or rewording
- [x] 2.4 Confirm the new test for 2.1 now fails against the current source
  (proving the check detects the live defect) before fixing the string

## 3. Fix the plural-hack msgid

- [x] 3.1 Change the `GtkToolButton` tooltip at `src/scantpaper/app.ui:533` from
  `Open image file(s)` to `Open images`
- [x] 3.2 Re-run `PYTHONPATH=src python3 dev/generate_pot.py` and confirm the
  active msgid count drops by one and no `(s)` msgid remains
- [x] 3.3 Confirm `python3 dev/check_po.py` passes with the hard check enabled
  and `pytest` is green

## 4. Advisory checks: catalog-side mistranslations

- [x] 4.1 Add a test asserting a `msgstr` equal to a different msgid in the same
  catalog is reported, and that validation still exits successfully
- [x] 4.2 Add a test asserting the self-variant discriminator suppresses the
  case-only case (`msgid "_Ok"` with `msgstr "_OK"`)
- [x] 4.3 Add a test for the sibling-must-differ condition
- [x] 4.4 Implement conditions (e)–(f) from the delta, reusing the existing
  `advisory_lines` channel so the exit code is unchanged
- [x] 4.5 Run the checker and confirm the measured findings are reported: 6 for
  (e) and 14 for (f), and that the 16 `_Ok`/`_OK` self-variant hits are absent

## 5. Advisory checks: source-wide

- [x] 5.1 Add tests for each source-wide condition: case-only-duplicate msgids,
  concatenation fragments, doubled space, Greek mu `U+03BC`, and msgids over
  200 characters
- [x] 5.2 Implement conditions (i)–(m) from the delta, evaluated once over the
  generated msgid set
- [x] 5.3 Add a test asserting `Both sides` / `Both sides.` is not reported, so
  the label/tooltip pattern cannot be mistaken for a near-duplicate later
- [x] 5.4 Run the checker and confirm each condition reports its measured
  current count (4 case pairs, 5 fragments, 1 doubled space, 1 mu, 4 long).
  Group 6 then reduces the case pairs to 2, since `_Ok`/`_OK` and `PPI`/`ppi`
  were each half of a pair. The remaining 2 pairs are `Scan Options`/
  `Scan options` and `Scan Document`/`Scan document`, which are correct as
  they stand (a title-cased window title and a sentence-cased button label).
  The single doubled space is deliberately left in place; see 6.4

## 6. Clear the defects the new checks report, so they start green

A check that fires on defects already known on day one trains reviewers to
ignore its output, so the unambiguous ones are fixed in the same change. Each
is a one-line edit with no design content.

- [x] 6.1 Unify the OK-button label on `_OK`: change
  `src/scantpaper/session_mixins.py:448` from `_("_Ok")` to `_("_OK")`,
  matching `src/scantpaper/text_layer_control.py:80`
- [x] 6.2 Unify the pixels-per-inch label on `ppi`: change
  `src/scantpaper/dialog/save.py:789` from `_("PPI")` to `_("ppi")`, matching
  `src/scantpaper/dialog/scan.py:660` and the lowercase `dpi`
- [x] 6.3 Update `src/scantpaper/tests/test_052_dialog_save.py:564`, which
  hardcodes the `"PPI"` label, to match
- [ ] 6.4 Remove the doubled space in the 2 GiB message at
  `src/scantpaper/savethread.py:291`. **Left undone on purpose.** The
  maintainer reverted it to keep the msgid stable while coordinating the
  msgid/msgstr changes with the catalog re-merge. Editing a msgid does not
  invalidate the other ~1,270 strings, but it does add one obsolete and one
  fuzzy entry per catalog, and the obsolete count is what trips
  `OBSOLETE_CEILING`. Tracked in `follow-ups.md` section 1
- [x] 6.5 Re-run the checker and confirm (i) drops from 4 to 2, leaving (j) at
  5, (k) at 1 and (l) at 1
- [x] 6.6 Confirm `python3 dev/check_po.py` still passes, `pytest` is green,
  coverage has not dropped, and `ruff`/`ty` are clean

## 7. Documentation

- [x] 7.1 Add one sentence to `AGENTS.md` requiring new user-visible strings to
  be considered for ease of translation: no embedded plural marker (use
  `ngettext()` for counted text), no translatable sentence-fragment
  concatenation, and run `dev/check_po.py` before committing
- [x] 7.2 Update the validation section of `README.md` to list the new
  hard-fail and advisory checks

## 8. Verification

- [x] 8.1 `python3 dev/check_po.py` — 44 catalogs, 0 errors, advisories printed
- [x] 8.2 `python3 -m pytest -q` — all pass, coverage not below 99.28%
- [x] 8.3 `ruff check` and `ruff format --check` clean on all touched files
- [x] 8.4 `ty check .` clean
- [x] 8.5 Record in `po/TRANSLATION-FINDINGS.md` that the structural detection
  described there is now automated, so the file is not mistaken for a
  one-off manual audit

## 9. Follow-ups

Deferred work is tracked in `follow-ups.md`, not here: the catalog re-merge and
its coupled ceiling changes, the five concatenation fragments, routing the
catalog-side advisories to native speakers, the obsolete-entry ratchet, the
`μs` encoding, the measured-and-rejected accelerator conditions, the two
standing advisories that are correct to keep, and the language-independent
catalog checks that were considered and deprioritised.
