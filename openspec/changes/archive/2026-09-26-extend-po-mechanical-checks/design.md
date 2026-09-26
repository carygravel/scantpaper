## Context

`dev/check_po.py` currently runs two gates per catalog: a subprocess
`msgfmt --check` and a regex read of the `Plural-Forms` header checked
against CLDR `nplurals`. It does not parse the message bodies itself.
Investigation for this change established, against the real catalogs:

- The app's printf translatable strings are all `%`-formatted at runtime.
  The POT carries 39 `#, python-format` entries and no `c-format`. Stale
  `#, perl-format` flags survive only inside obsolete `#~` blocks, never in
  shipped entries. `{}`/`.format()` translatable strings are not used yet,
  but the maintainer now intends to, so a `{}` guard is a precondition for
  that adoption.
- `msgfmt --check` does not reject `"% s"`/`"% d"`/`"% i"` in printf-flagged
  strings. **14 such tokens exist in shipped (non-obsolete) entries, all in
  Italian**; 9 Italian and 1 Galician additional occurrences live only in
  obsolete `#~` blocks. None appear in any `msgid` or in `en_*`.
- For `{}` strings `msgfmt` checks *nothing* (verified: it exits 0 on a
  `"{count} in {dir}"`→`"{ count } dans {dir}"` rename). Python's stdlib
  `string.Formatter().parse()` is the robust validator: it raises
  `ValueError` on malformed braces and returns exact field names otherwise;
  note `{ name }` parses (field name `' name '`) but breaks `.format()` with
  `KeyError`, so structural parsing plus field-name equality are both needed.
- 3037 obsolete `#~` entries, a per-catalog number of `#, fuzzy` entries
  whose `msgstr` is empty, and one non-NFC `msgstr` (el) are all invisible to
  the present gate.
- `polib` is already a declared test extra and imports cleanly (v1.2.0);
  `string.Formatter` is stdlib.

See proposal.md - Why for motivation.

## Goals / Non-Goals

**Goals:**
- Add a format-placeholder integrity gate covering both styles: the printf
  `%`-space class (any `*-format` flag; zero false positives, incl. `%%`-escaped
  and positionally reordered strings), and `{}`/`.format()` fields (structural
  parseability + field-name equality) so `{}` can be adopted safely.
- Add an advisory hygiene report (obsolete count, empty-fuzzy count, non-NFC
  count, bare-`{}` multi-field reorder hazard) that never fails CI on the
  existing backlog.
- Keep CI green at the moment the gate is merged.

**Non-Goals:**
- Auto-purging obsolete entries from the catalogs (a large, separate churn);
  this change only reports them.
- Changing the `Plural-Forms`/`msgfmt` logic already shipped.
- Repairing *wording* of any translation (see Decisions - D2 for why the 22
  fixes are not "translation" edits).
- Handling `c-format` tokens (none occur and none are planned; the printf arm
  targets `python-format`, which is what xgettext emits here).

## Decisions

### D1 — Parse with polib, not regex or msgcat

Add a polib pass in `check_po.py` (`polib.pofile(path)`) to iterate entries
and read the `*-format` flags (from `entry.flags`), `fuzzy`, and the
per-plural `msgstr` list, and use stdlib `string.Formatter().parse()` for `{}`
fields. polib handles multi-line, escaped, and plural bodies that a
hand-rolled regex gets wrong (a throwaway regex parser had to be corrected
twice during exploration). polib separates obsolete entries via
`obsolete_entries()`, so the check naturally ignores `#~` blocks. polib is
already a test-only dependency, so no new runtime dependency is introduced;
`string.Formatter` is stdlib.
*Alternatives considered:* extend the existing msgfmt subprocess (rejected —
msgfmt is exactly the weak validator being supplemented); `msgcat`/`msgunfmt`
post-processing (rejected — gettext offers no token-validity check).

### D2 — Token predicate is narrow; the 22 fixes ride in the same commit

Flag a printf entry (any `*-format` flag) only when the body matches
`%\s+[diouxXeEfgGaAcspn]` (a `%` followed by whitespace then a conversion
letter). This deliberately ignores legitimate space flags that the app does
not use, `%%`, and positional `%n$` reordering. Because the gate fails
immediately on the existing 24 strings, they must be repaired in the same
change so CI stays green: each repair deletes the single spurious space
(`"% s"`→`"%s"`) and restores any adjacent literal spacing the translator
dropped (`"...:% s"`→`"...: %s"`). This is a mechanical formatting fix, not a
re-translation, so it does not touch the human-authored wording and is not
governed by the fuzzy rule (which is about *adding* translations).
*Alternative:* an allow-list to defer the fixes — rejected as debt that hides
live rendering defects.

### D3 — Obsolete ceiling is a ratchet, advisory counts always print

The hygiene pass reports per-catalog counts for obsolete entries, empty-fuzzy
entries, and non-NFC bodies. Only the obsolete count is gated, via a
per-catalog ceiling constant initialised at the current count so the build
fails only if the count *grows*. The ceiling is expected to ratchet downward
over time.
*Alternative:* fail on any obsolete entry — rejected (3037 pre-existing; the
goal is regression control, not a red build).

### D4 — Tier separation lives in one exit code path

`check_po.py` keeps its existing "return non-zero on failure" contract.
Hard-gate failures (msgfmt, Plural-Forms, token integrity) increment the
error count; hygiene items print an `[advisory]` line and only the obsolete
ceiling breach adds to the error count.

### D6 — `{}` arm: parse + field-name equality; require indexed/named fields

An entry is treated as a `.format()` string when its `msgid` yields at least
one field from `Formatter().parse()`. For each non-empty `msgstr`:
(a) `Formatter().parse()` must not raise (structural well-formedness); and
(b) the multiset of field names from the `msgstr` must equal the `msgid`'s.
`{{`/`}}` are literal escapes and produce no field, so they are excluded.
This catches dropped/extra/renamed/whitespace-corrupted fields — the classes
`msgfmt` cannot see.

Adoption convention (advisory, condition (d) of D3): a `msgid` with **more
than one** field must use **indexed or named** fields (`{0}`, `{name}`), never
bare `{}`. Bare `{}` carries an empty field name, so translators cannot
reorder arguments to fit target-language word order — the exact reason `{}`
was previously avoided here. A single bare `{}` is fine, so this is advisory,
not a hard gate. The hard parts of this decision are (a) and (b); the
convention is the guidance that makes `{}` translation-safe.
*Alternative:* auto-renumber bare `{}` to positional — rejected as too magic;
the convention is simpler to state and test.

### D7 — Exclude obsolete entries: polib leaks them into the active iteration

polib lists shipped entries via `for entry in po`, but a defect means an
obsolete (`#~`) entry can leak into that iteration when a stray flag comment
(`#, perl-format`) precedes the `#~ msgid`. Such strings never compile into a
`.mo`, so treating them as live defects is both a false failure and — because
the fix would rewrite a `#~` line — a meaningless edit. Every placeholder and
hygiene pass therefore iterates a filtered active set: entries whose
`(msgctxt, msgid, msgid_plural)` key also appears in `po.obsolete_entries()`
are dropped. Verified: without the filter the check reports 24; with it, the
14 shipped defects only.
*Alternative:* raw-text parsing to avoid polib entirely — rejected; the
leak is one narrow, handled case and polib still gives correct multi-line and
plural decoding for everything else.

## Risks / Trade-offs

- **[Over-eager `%` regex] → false-positive CI failures.** Mitigated by the
  narrow predicate (must be `%` + whitespace + a conversion letter, and only
  on `*-format` entries), validated to yield exactly the 14 known hits and
  zero elsewhere.
- **[polib not on the CI runner]** → `test_po_files.py` already relies on the
  `test` extra; polib is listed there, so the dependency is satisfied in CI.
- **[Fixing shipped strings] → maintainer review needed.** All 14 edits are
  single-space deletions; the full diff is reviewed in one commit before
  merge, so the human gate is preserved.
- **[Ratchet ceiling drift]** → if obsolete counts are legitimately reduced,
  the constant must be lowered with the change; documented in tasks as a
  manual step.
- **[`Formatter().parse()` differs from `str.format()`]** → `parse()` accepts
  some field names that a real `.format(**kwargs)` call could still fail on
  (e.g. an attribute/index the runtime lacks). Mitigated by also enforcing
  field-name multiset equality against the `msgid`, so a translated field
  cannot name something the source never used.
- **[Literal braces in a non-format string]** → a `msgid` containing only
  `{{`/`}}` has no fields and is correctly skipped; a genuinely literal single
  `{` is invalid in `str.format` anyway, so flagging it is correct.
