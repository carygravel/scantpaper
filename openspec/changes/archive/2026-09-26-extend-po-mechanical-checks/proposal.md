## Why

`dev/check_po.py` (added in `po-catalog-validation`) runs `msgfmt --check`
and validates the CLDR `Plural-Forms` header. `msgfmt --check` catches
`msgid`/`msgstr` specifier drift for `c-format` strings, but its
`python-format` validation is weak: it accepts malformed tokens such as
`"% s"` / `"% d"` that Python's `%` operator tolerates but renders
incorrectly. A scan of the *shipped* (non-obsolete) catalogs found **14 such
tokens**, all in Italian, in active non-fuzzy `msgstr`s (zero in any `msgid`
and zero in `en_US`/`en_GB`). Each is a user-visible rendering defect: for
`%s` the intervening space is silently dropped (`"...:% s"` renders as
`"...:value"` with the space lost), and for `%d`/`%i` the space acts as the
printf space flag and injects a leading space (`"% d"` → `" 5"`). A further
9 Italian and 1 Galician occurrence sit only in obsolete `#~` blocks and never
compile into a `.mo` — so the gate must ignore obsolete entries, and a real
defect in the tooling (polib leaks such an entry into the active iteration
when a stray `#, perl-format` comment precedes a `#~ msgid`) had to be fixed
(see design.md D7). Three lower severity catalog-hygiene defects (thousands of
dead `#~` entries, fuzzy flags on empty strings, and out-of-NFC text) are
likewise invisible to `msgfmt`.

In addition, the app will begin using Python `.format()`/`{}`-style
translatable strings. These are not covered by the `python-format` flag
(which gettext reserves for `%`-style printf) and are therefore checked by
**nothing**: `msgfmt --check` exits 0 even when a translated `msgstr` renames
or drops a field (e.g. `"{count} in {dir}"` → `"{ count } in {dir}"`, which
raises `KeyError: ' name '` the first time it is formatted). A token-integrity
check is the precondition for adopting `{}` safely; the reorder hazard that
historically made `{}` translation-hostile is addressed by requiring
indexed/named fields (see design.md D6).

## What Changes

- Extend `dev/check_po.py` with a **format-token integrity check** covering
  both placeholder styles:
  - For any entry carrying a `*-format` flag (all current active hits are
    `python-format`; the stale `perl-format` flags appear only on obsolete
    entries, which the gate ignores): every non-empty `msgstr` must use
    well-formed printf tokens; a `%` separated from its conversion letter by
    whitespace fails the build (the `msgfmt --check` printf gap).
  - For entries whose `msgid` contains `{}`/`{name}`/`{0}` replacement fields
    (no gettext flag exists for these): each `msgstr` must parse with
    `string.Formatter().parse()` (no malformed brace) **and** carry the same
    multiset of field names as the `msgid`. This lets `{}` be adopted safely.
- Add an **advisory housekeeping report** (does *not* fail the build) that
  surfaces, per catalog: obsolete `#~` entry counts (with a growth ceiling),
  fuzzy flags on entries whose `msgstr` is empty, any `msgstr` not in Unicode
  NFC form, and `msgid`s that use a bare `{}` when the string has more than
  one field (unreorderable by translators — use `{0}`/`{name}` instead).
- Add unit tests for each new check and wire them into the existing
  `test_po_files.py` CI job.

The two tiers are deliberately separate: the integrity check is a hard gate
(deterministic, and for the 14 existing `%` tokens the fix is a single
deleted space); the housekeeping items are advisory only, so a large
pre-existing backlog (e.g. 3037 obsolete entries) does not turn CI red
overnight. No `{}` defects exist yet, so adding that arm turns nothing red
today — it is the guard that *lets* `{}` be adopted.

## Capabilities

### New Capabilities

_None — this extends an existing capability._

### Modified Capabilities

- `translations`: adds two requirements to the mechanical-validation
  behaviour — malformed format placeholders (both `%` printf tokens and
  `{}` replacement fields) must fail validation (hard gate), and
  catalog-hygiene defects must be reported (advisory). The existing
  "Translation catalogs are mechanically validated" requirement is unchanged.

## Impact

- **Code:** `dev/check_po.py` (new checks + output tiers).
- **Tests:** `src/scantpaper/tests/test_po_files.py` (new cases).
- **CI:** `.github/workflows/test.yml` already invokes the check; a format
  token in it will now fail until the 14 strings are fixed.
- **Data:** the 14 malformed Italian `%` `msgstr` entries are repaired as
  mechanical single-space deletions in the same change that adds the gate (so
  CI is green on merge); this is a formatting fix, not a re-translation, and
  does not touch the fuzzy-authorship rule. The 9 obsolete Italian and 1
  obsolete Galician occurrences are left in place (never shipped). There is
  no `{}` backlog to fix (none exist yet).
- **Source:** the new `{}` arm enables `.format()` translatable strings going
  forward; existing `%`-style strings are unaffected.
- **No new dependencies** — parsing uses `polib` (already a test extra) and
  `string.Formatter` (stdlib).
