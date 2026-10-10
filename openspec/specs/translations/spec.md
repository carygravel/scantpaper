# translations

## Purpose

Defines how scantpaper's translations are produced, marked, and shipped:
fuzzy-marked translations are treated as untranslated until a human confirms
them, and only non-fuzzy translations reach end users.

## Requirements

### Requirement: Fuzzy translations fall back to English
The system SHALL treat a `#, fuzzy` translation as untranslated, so users see
the English source string for that message until the fuzzy flag is cleared.

#### Scenario: Fuzzy string is displayed to user
- **WHEN** a catalog contains a `#, fuzzy` entry for a message and the user
  runs the application in that language
- **THEN** the user sees the English source text for that message, not the
  fuzzy translation

#### Scenario: Non-fuzzy translation is displayed to user
- **WHEN** a catalog contains a non-fuzzy entry for a message and the user
  runs the application in that language
- **THEN** the user sees the translated text for that message

### Requirement: Only non-fuzzy translations ship
Release builds SHALL include only non-fuzzy translations; fuzzy entries SHALL
never be compiled into a released catalog.

#### Scenario: Release with fuzzy entries present
- **WHEN** a release is built while a catalog still contains fuzzy entries
- **THEN** the release is built successfully with those messages falling back
  to English, and the release is not blocked by the fuzzy entries

#### Scenario: Fuzzy entries never appear in released output
- **WHEN** a released catalog is inspected for a message that is fuzzy in the
  source catalog
- **THEN** the fuzzy translation is absent from the released output and the
  English fallback is used instead

### Requirement: Missing translations may be added as fuzzy
The translation workflow SHALL allow missing strings to be translated and
marked `#, fuzzy` (needing review) rather than left untranslated.

#### Scenario: Translator confirms a fuzzy string
- **WHEN** a human translator reviews a fuzzy entry and clears its fuzzy flag
- **THEN** the entry becomes a shipped translation for the next release

#### Scenario: Fuzzy entry remains unreviewed
- **WHEN** a fuzzy entry has not been reviewed by a translator
- **THEN** it continues to fall back to English and is excluded from releases

### Requirement: Translation updates flow through Rosetta
The system SHALL continue to use the Rosetta (Launchpad) workflow to download
translated catalogs and receive cleared (non-fuzzy) translations before a
release.

#### Scenario: Translated catalog downloaded from Rosetta
- **WHEN** translated `.po` files are downloaded from Rosetta before a release
- **THEN** the confirmed translations are included in the release and
  unreviewed fuzzy entries continue to fall back to English

### Requirement: Translation catalogs are mechanically validated
The system SHALL validate every translation catalog mechanically before it
is accepted: each `po/*.po` SHALL pass `msgfmt --check` (format-specifier
consistency between `msgid` and `msgstr`, escape-sequence correctness, and
plural-entry counts) and SHALL declare a `Plural-Forms` header that matches
the CLDR plural rules for its language (e.g. `nplurals=3` for
ru/uk/pl/be/sr/cs/sk, `nplurals=4` for sl, `nplurals=6` for ar). The check
SHALL run in CI and fail the build on any violation.

#### Scenario: Catalog with placeholder drift is rejected
- **WHEN** a catalog contains a translated string whose format specifiers
  do not match its source string
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: Catalog with wrong plural forms is rejected
- **WHEN** a catalog declares a `Plural-Forms` header that does not match
  the CLDR plural rules for its language
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: Valid catalog passes
- **WHEN** a catalog passes `msgfmt --check` and declares the correct
  `Plural-Forms` header for its language
- **THEN** the mechanical validation succeeds

### Requirement: Malformed format placeholders fail catalog validation
The mechanical catalog validation SHALL reject entries whose translated
text contains a malformed format placeholder, for both placeholder styles
the application uses, and SHALL fail the build in CI on any violation.

For printf style (any entry carrying a `*-format` flag): a `msgstr` SHALL
NOT contain a `%` separated from its conversion letter by whitespace (e.g.
`"% s"`, `"% d"`), which `msgfmt --check` accepts under its printf modes but
which renders incorrectly at runtime. The check SHALL ignore legitimate
positional reordering such as `%2$s ... %1$d` and the literal `%%` escape.

For `str.format` style (any entry whose `msgid` contains a `{...}`
replacement field; gettext has no flag for these, so `msgfmt` validates
nothing): each non-empty `msgstr` SHALL parse without error under
`string.Formatter().parse()` and SHALL carry the same multiset of
replacement-field names as the `msgid`. A renamed, whitespace-corrupted
(`"{ count }"` vs `"{count}"`), dropped, or extra field SHALL fail
validation. The literal `{{`/`}}` escapes SHALL NOT be counted as fields.

Obsolete (`#~`) entries never compile into a released catalog, so the
validation SHALL ignore them: only shipped (non-obsolete) entries are
checked, and an obsolete entry that a parser surfaces among active ones
SHALL be excluded from these checks.

#### Scenario: python-format entry with a spaced token is rejected
- **WHEN** a catalog contains a `#, python-format` entry whose `msgstr` is
  `"...% s..."` while the `msgid` is `"...%s..."`
- **THEN** the mechanical validation fails and CI fails the build

#### Scenario: printf positional reordering passes
- **WHEN** a `python-format` entry's `msgstr` uses only well-formed printf
  tokens, including a legitimate positional reordering such as `%2$s ... %1$d`
- **THEN** the format-placeholder check succeeds for that entry

#### Scenario: format entry whose msgstr renames a field is rejected
- **WHEN** a `msgid` is `"{count} in {dir}"` and its `msgstr` is
  `"{ count } dans {dir}"`
- **THEN** the field-name multiset differs, validation fails, and CI fails
  the build

#### Scenario: format entry with a malformed brace is rejected
- **WHEN** an entry's `msgid` contains a `{...}` field and its `msgstr` has
  an unbalanced brace such as `"{value"`
- **THEN** `string.Formatter().parse()` errors and validation fails the build

#### Scenario: format entry with matching fields passes
- **WHEN** a `msgid` is `"{0} and {1}"` and its `msgstr` reorders to
  `"{1} et {0}"` (indexed fields)
- **THEN** the field-name multisets match and validation succeeds

#### Scenario: entry with no placeholders is unaffected
- **WHEN** an entry's `msgid` contains neither a printf token nor a `{}`
  field and the `msgstr` introduces a stray `%` or `{`
- **THEN** this check does not report the entry and the validation outcome is
  unchanged

### Requirement: Untranslatable plural-hack msgids fail validation
The mechanical validation SHALL reject any source msgid that embeds a
parenthesised plural suffix immediately following a word character, such as
`Open image file(s)` or `Save page(s)`. Such a string is not a counted
message, so it cannot be expressed with `ngettext()`, yet it also has no
portable equivalent in languages whose plural morphology the bare `(s)`
cannot represent. The validation SHALL fail the build in CI on any such
msgid.

Parenthesised text that is not a bare plural suffix SHALL NOT be flagged.
In particular a parenthesised unit, abbreviation or gloss such as `(Mb)`,
`(DCT)` or `(regular expression)` is a legitimate construction.

#### Scenario: msgid with a parenthesised plural suffix is rejected
- **WHEN** the source msgid set contains a msgid such as
  `"Open image file(s)"`
- **THEN** the mechanical validation fails and CI fails the build, naming the
  offending msgid

#### Scenario: parenthesised unit or gloss is not flagged
- **WHEN** a msgid contains a parenthesised unit, abbreviation or gloss such
  as `"Warn if available space less than (Mb)"` or
  `"Compress output with JPEG (DCT) encoding."`
- **THEN** the plural-hack check does not report it and the validation
  outcome for that string is unchanged

#### Scenario: counted text expressed with ngettext passes
- **WHEN** a message requires plural forms and is expressed as a counted
  msgid with a plural msgid and per-form msgstr entries rather than with a
  parenthesised suffix
- **THEN** the plural-hack check succeeds for that message

### Requirement: Catalog hygiene defects are reported
The mechanical catalog validation SHALL report the following hygiene
conditions that `msgfmt --check` does not, and SHALL report them without
failing the build.

*Per catalog:*

(a) the count of obsolete `#~` entries; (b) entries carrying a `#, fuzzy`
flag whose `msgstr` is empty; (c) any `msgstr` text that is not normalised to
Unicode NFC form; (d) any `msgid` that uses a bare `{}` replacement field
while the string contains more than one field; (e) any `msgstr` equal to a
*different* msgid in the same catalog, which is the signature of a bad
`msgmerge` fuzzy binding; (f) any pair of sibling msgids that must differ
(for example `Select Odd` and `Select Even`) whose translations are
identical.

A `msgstr` in (e) SHALL NOT be reported when it differs from its own msgid
only by case or by the position of the accelerator marker, since such a
difference is a plausible rendering of the same label rather than a
mismatched string.

*Reported once over the source msgid set, not per catalog:*

(i) any two msgids that differ only by letter case, for example
`Scan Options` and `Scan options`; (j) any msgid that is a concatenation
fragment, meaning it ends with a colon and trailing whitespace or newline and
carries no placeholder, for example `"Error opening device: "` or
`"The following paper sizes are too big to be scanned by the selected
device:"`. Such a fragment is intended to be concatenated with a runtime value
or list, which pins the word order of the sentence to English and prevents a
locale from placing the list elsewhere; (k) any msgid containing a doubled space
that is not a deliberate sentence break; (l) any msgid using U+03BC GREEK SMALL
LETTER MU where U+00B5 MICRO SIGN may be intended; (m) any msgid longer than
200 characters, reported as a translation effort warning.

The obsolete-entry count in (a) SHALL be subject to a configurable ceiling
initialised at or above the current total, so that the build fails only when
the count *grows* beyond the ceiling, not because of the pre-existing
backlog. Condition (d) is advisory rather than a hard gate because a bare
`{}` with a single field is legitimate; it flags only the multi-field case,
which translators cannot reorder safely and should express as `{0}`/`{1}` or
named fields. Conditions (e) and (f) are advisory because neither can
author the correct translation: they identify a string for human review, and
the reviewer supplies the wording.

Conditions on keyboard accelerators are NOT part of this requirement. A
translation is entitled to relocate its mnemonic onto a character that exists
in its own script, so neither the accelerator letter nor its presence in the
translation is a reliable defect signal: measured against the 44 catalogs,
requiring the letter to match flagged 558 entries that were all correct
translations, and treating an absent marker as a defect produced 315 entries
whose language and review status could not be established. Neither condition
can be acted on without a native reviewer, and this project has no reliable
one, so no accelerator condition is specified.

The source msgid set used by (i) through (m) SHALL be generated on demand
rather than read from a committed file, so that the checks reflect the current
source even when the message template has not been regenerated.

#### Scenario: hygiene issues are reported without failing
- **WHEN** a catalog contains obsolete entries, empty-fuzzy entries,
  out-of-NFC text, or a multi-field bare `{}` `msgid`, and is within the
  configured obsolete ceiling
- **THEN** validation prints the per-catalog counts and exits successfully

#### Scenario: obsolete backlog growth is rejected
- **WHEN** a change adds obsolete `#~` entries such that a catalog's count
  exceeds its configured ceiling
- **THEN** validation fails the build, signalling a regression rather than
  the existing backlog

#### Scenario: mistranslation copied from another msgid is reported
- **WHEN** a catalog translates `Select Odd` as the same text it uses for
  `Select Even`, and that text is the `msgstr` of a different entry
- **THEN** the condition is reported for that catalog and validation exits
  successfully

#### Scenario: msgstr differing only in case from its own msgid is not reported
- **WHEN** an entry's msgid is `"_Ok"` and its `msgstr` is `"_OK"`, which is
  also a msgid in the same catalog
- **THEN** the mistranslation condition is not reported for that entry,
  because the difference from its own msgid is case only

#### Scenario: source msgid defects are reported once
- **WHEN** the source msgid set contains both `"Scan Options"` and
  `"Scan options"`, a log prefix `"Error opening device: "`, and a msgid such
  as `"The following paper sizes are too big to be scanned by the selected
  device:"` that a caller concatenates with a list
- **THEN** each condition is reported once for the source msgid set, without
  being repeated per catalog, and validation exits successfully

#### Scenario: a concatenation fragment is detected whether or not it ends
in a space
- **WHEN** the source msgid set contains a msgid ending in `": "` and one
  ending in `":"` with no trailing space
- **THEN** the concatenation-fragment condition is reported for both, because
  both are intended to be followed by a runtime value or list

#### Scenario: legitimate label and tooltip pairs are not reported
- **WHEN** the source msgid set contains `"Both sides"` and
  `"Both sides."`, which are a label and its tooltip rather than a
  near-duplicate defect
- **THEN** no near-duplicate condition is reported for that pair

### Requirement: The message template is generated with a vendored ITS rule set
The message template generator SHALL extract translatable strings from the
project's Glade/GtkBuilder `.ui` files using gettext's ITS extraction rules
for GtkBuilder XML, taken from a copy of those rules vendored in the
repository rather than from the copy installed on the system. Generation
SHALL NOT require `intltool`, and `gettext` SHALL be the only external tool
the catalog checks need.

The generated msgid set SHALL be unaffected by the mechanism: no msgid may be
added or removed relative to what the `intltool`-based pipeline produced.

The vendored rules exist so that extraction depends on neither the gettext
version nor its install layout. Because a copy can therefore drift from
upstream, the validation SHALL compare the vendored rules against the
installed copy and report any difference. That comparison SHALL be advisory
and SHALL NOT fail the build: a difference means this project's copy may be
behind, not that the generated template is wrong, and the project does not
block a release on a condition that identifies no defect in shipped output.
The report SHALL name both files and state whether the installed copy is
absent, so an absent copy is distinguishable from an identical one.

#### Scenario: generation succeeds without intltool installed
- **WHEN** the message template is generated on a system with `xgettext`,
  `msgcat` and `msgfmt` present but `intltool-extract` absent
- **THEN** generation succeeds and the resulting msgid set contains the
  translatable strings from the `.ui` files

#### Scenario: the extracted msgid set is unchanged by the mechanism
- **WHEN** the msgid set generated with the vendored ITS rules is compared
  with the set produced by the `intltool`-based pipeline it replaces
- **THEN** the two sets contain exactly the same msgids, with none present in
  only one of them

#### Scenario: vendored rules differ from the installed copy
- **WHEN** the ITS rules installed on the system differ in content from the
  vendored copy
- **THEN** the difference is reported, naming both files, and validation exits
  successfully

#### Scenario: no ITS rules are installed on the system
- **WHEN** the system has no copy of the GtkBuilder ITS rules to compare
  against
- **THEN** the report states that no installed copy was found, which is
  distinguishable from a matching copy, and generation still uses the
  vendored rules

#### Scenario: `.ui` strings are missing from the generated set
- **WHEN** the generated msgid set contains none of the translatable strings
  from the `.ui` files, for instance because the ITS rules cannot be resolved
- **THEN** validation fails, rather than reporting a clean result over a set
  that silently omits every string from the user interface definition

### Requirement: Upstream changes are detected against a baseline
The project SHALL provide a check that compares the current public Launchpad
state of the `scantpaper` translation template, and of each of its languages,
against a committed baseline, and reports every unit that has changed since the
baseline was last advanced. The check SHALL NOT authenticate to Launchpad, and
SHALL NOT attempt to download any translation catalog, because Launchpad
requires a logged-in session to export a catalog.

The check SHALL detect two independent triggers, each read from the only public
surface that carries it:

- the **template** (the message set), from the Launchpad JSON API resource for
  the translation template, using the template's `date_last_updated` and its
  HTTP entity tag, with a conditional request so that an unchanged template is
  detected without transferring a response body;
- **per-language translation activity**, from the public series translation
  page, whose per-language last-changed timestamps exist on no other public
  surface. This page SHALL be read on every run, because a translation can
  change without the template changing.

The baseline SHALL record the values Launchpad reported at the last sync, and
SHALL be advanced only by a distinct, explicit action, so that it continues to
represent the upstream state the catalogs were last synced from rather than the
latest state observed.

#### Scenario: The message set changed
- **WHEN** the template's entity tag or `date_last_updated` differs from the
  baseline and the series translation page is readable
- **THEN** the check reports that the template changed and exits successfully

#### Scenario: A translation changed but the template did not
- **WHEN** the template's entity tag matches the baseline but a language's
  last-changed time on the series translation page is newer than that language
  in the baseline
- **THEN** the check reports that language as changed, with its new
  untranslated and unreviewed counts, and exits successfully

#### Scenario: Nothing changed
- **WHEN** the template matches the baseline and every language's last-changed
  time equals its value in the baseline
- **THEN** the check reports that there is nothing new and exits successfully

#### Scenario: A new language appears
- **WHEN** the series translation page lists a language that is absent from the
  baseline
- **THEN** the check reports that language as new

#### Scenario: No catalog is downloaded
- **WHEN** the check runs, whether or not a change is detected
- **THEN** it sends no request to any Launchpad catalog export endpoint and
  provides no credentials

#### Scenario: Baseline is advanced only when asked
- **WHEN** the check runs without the explicit baseline-advancing option and a
  change is present
- **THEN** the committed baseline is left unchanged and the next run reports the
  same change again

#### Scenario: Baseline is advanced after a sync
- **WHEN** the check runs with the explicit baseline-advancing option after the
  catalogs have been synced
- **THEN** the baseline records the current template and per-language values,
  and a subsequent run reports that there is nothing new

### Requirement: Local message template staleness is detected against a baseline
The check SHALL also report when the locally generated message template (the
`.pot` regenerated from source) has moved relative to the message set of the
last pot uploaded to Launchpad, so the maintainer knows a new pot is ready to
push up. This is the reverse of the existing upstream-change check, and SHALL
be answered entirely from local state: the baseline records the fingerprint of
the last uploaded pot, and the check compares the freshly generated message set
against that fingerprint. It SHALL NOT attempt to read the pot's message set
from Launchpad, which would require authentication.

The fingerprint SHALL be derived from the message set only: the sorted, unique
`msgid` strings extracted from the generated template, ignoring the template's
volatile header (creation date, package version) and the `#: file:line`
reference comments. A difference that leaves the message set unchanged — for
example a string moved between source files, or a different gettext version
reordering output — SHALL NOT count as a change.

The baseline SHALL record the fingerprint of the last uploaded pot, and SHALL
be advanced only by a distinct, explicit stamping action taken after a pot has
actually been uploaded, mirroring the upstream `--update` action. When no pot
has been recorded yet, the check SHALL report the local state as not
determined rather than as unchanged.

#### Scenario: New source strings are ready to upload
- **WHEN** the locally generated message set contains an `msgid` that is
  absent from the recorded uploaded-pot fingerprint
- **THEN** the check reports that the local template is stale, names the
  change, and exits successfully

#### Scenario: Only line references moved
- **WHEN** a string is moved between source files so its `#: file:line`
  reference changes but the set of `msgid` strings is unchanged
- **THEN** the check reports no local template change

#### Scenario: Only volatile headers changed
- **WHEN** regenerating the template changes its creation date or package
  version header but the set of `msgid` strings is unchanged
- **THEN** the check reports no local template change

#### Scenario: Reordering is ignored
- **WHEN** a different gettext version emits the same `msgid` set in a
  different order
- **THEN** the check reports no local template change, because the sorted
  fingerprint is unchanged

#### Scenario: Local fingerprint is stamped after an upload
- **WHEN** the check runs with the explicit stamp-after-upload option after a
  new pot has been uploaded
- **THEN** the baseline records the fingerprint of the uploaded pot, and a
  subsequent run reports no local template change

#### Scenario: No pot recorded yet is not unchanged
- **WHEN** the baseline contains no recorded uploaded-pot fingerprint and the
  check runs
- **THEN** the check reports the local template state as not determined rather
  than as unchanged

### Requirement: Undetermined state is distinct from unchanged
The check SHALL NOT report a unit as unchanged unless it actually read that
unit's current state. When it cannot determine a unit's state — because a
request failed, the API returned an unexpected shape, or the series translation
page could not be parsed into language records — it SHALL report that unit as
not determined and SHALL exit non-zero, which is distinguishable from both
"changed" and "unchanged". A unit that could be read SHALL still be reported.

The check SHALL NOT be wired into the release gate: the default exit SHALL be
successful when the state was read, whether or not a change was found. CI MAY
request a non-zero exit on change through an explicit option.

Requests issued by the check SHALL identify the tool with a descriptive
`User-Agent` and SHALL be limited to those needed to answer the question: one
request to the API for the template and one to the series translation page.

#### Scenario: The series translation page cannot be parsed
- **WHEN** the template read succeeds but the series translation page's
  structure no longer matches what the parser expects
- **THEN** the check reports the template result, reports the per-language
  detail as not determined, and exits non-zero

#### Scenario: The API cannot be read
- **WHEN** the API request fails, times out, or returns an unexpected shape
  such that the template state cannot be determined
- **THEN** the per-language result is still reported and the check exits
  non-zero

#### Scenario: Undetermined state does not advance the baseline
- **WHEN** the check is asked to advance the baseline but any part of the state
  could not be determined
- **THEN** it refuses and leaves the baseline unchanged

#### Scenario: A change does not fail the default run
- **WHEN** the check detects that a change occurred and is run without the
  explicit fail-on-change option
- **THEN** it prints its report and exits successfully

#### Scenario: Explicit fail-on-change
- **WHEN** the check is run with the fail-on-change option and a change is
  detected
- **THEN** it exits non-zero, and when no change is detected it exits zero

#### Scenario: Requests are identified and bounded
- **WHEN** the check runs
- **THEN** each request carries a `User-Agent` naming the tool, and the run
  issues exactly one API request and one translation-page request
