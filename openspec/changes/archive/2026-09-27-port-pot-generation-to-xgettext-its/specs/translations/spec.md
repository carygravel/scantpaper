## ADDED Requirements

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
