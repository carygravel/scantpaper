## 1. Format-placeholder integrity check (hard gate)

- [x] 1.1 In `test_po_files.py`, add failing tests for both styles: a
      `python-format` entry whose `msgstr` is `"...% s..."` for `msgid`
      `"...%s..."` is rejected while `%2$s … %1$d` reordering and `%%` pass; a
      `{}` entry whose `msgstr` renames a field (`"{count} in {dir}"` →
      `"{ count } dans {dir}"`) or has an unbalanced brace is rejected while
      `{0}/{1}` reordering passes and `{{ }}` literals are ignored.
- [x] 1.2 Add printf token scan to `dev/check_po.py` using polib: for every
      entry carrying a `*-format` flag (excluding obsolete entries per
      D7), flag any `msgstr` matching `%\s+[diouxXeEfgGaAcspn]`; count it as a hard error and print
      `[FAIL] <file>: <msgid> -> <offending msgstr>`.
- [x] 1.3 Add the `{}` arm: when a `msgid` yields ≥1 field via
      `string.Formatter().parse()`, require each non-empty `msgstr` to (a)
      parse without raising and (b) have a field-name multiset equal to the
      `msgid`'s; count violations as hard errors with the same `[FAIL]` line.
- [x] 1.4 Run `python3 dev/check_po.py` and confirm the printf arm reports
      exactly the 14 shipped hits (all Italian) and the `{}` arm reports none
      (no `{}` strings exist yet).
- [x] 1.5 Repair the 14 shipped strings: delete the spurious space after `%` and
      restore any dropped adjacent literal space (e.g. `sconosciuto:% s` →
      `sconosciuto: %s`). Mechanical single-space edits only.
- [x] 1.6 Re-run `python3 dev/check_po.py` and confirm 0 placeholder failures
      from both arms.

## 2. Obsolete-entry ceiling (gated) + hygiene report

- [x] 2.1 Add a test: obsolete count above the per-catalog ceiling fails; a
      count at/below the ceiling passes and prints an `[advisory]` line.
- [x] 2.2 In `check_po.py`, count `po.obsolete_entries()` per catalog and
      compare against a module-level ceiling dict initialised to the current
      counts; only growth is a hard error.
- [x] 2.3 Record the current per-catalog obsolete totals in the ceiling dict
      and note in `design.md` that the constant only ratchets downward.

## 3. Empty-fuzzy, non-NFC and bare-`{}` advisory counts

- [x] 3.1 Add a test that empty-fuzzy, non-NFC `msgstr`, and a multi-field
      bare-`{}` `msgid` each produce `[advisory]` output without changing the
      exit code.
- [x] 3.2 In `check_po.py`, count entries with `fuzzy` and no non-empty
      `msgstr`, and any body where `unicodedata.is_normalized("NFC", s)` is
      False; print per-catalog `[advisory]` counts only.
- [x] 3.3 In `check_po.py`, advisory-flag any `msgid` whose
      `Formatter().parse()` yields more than one field with an empty field
      name (bare `{}`), pointing authors at `{0}`/`{name}` for reorderability.

## 4. Integration and quality gates

- [x] 4.1 Confirm `.github/workflows/test.yml` runs the extended
      `test_po_files.py` unchanged (new behaviour is inside `check_po.py`).
- [x] 4.2 Run `pytest` (full suite) and confirm green with coverage no worse
      than the current threshold.
- [x] 4.3 Run `ruff format` and `ruff check`; resolve any new lint findings
      without `noqa`/`per-file-ignores`.
- [x] 4.4 Run `ty check .` and confirm no new diagnostics.

## 5. Documentation

- [x] 5.1 Note the new checks in the AGENTS.md translations workflow only if
      the human-facing process changes (it does not); otherwise record the
      gate behaviour in the catalog-validation spec via archive.
- [x] 5.2 Update the proposal/spec `Translation catalogs are mechanically
      validated` wording during `openspec archive` to fold in the new
      requirements.
