## ADDED Requirements

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

## MODIFIED Requirements

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
