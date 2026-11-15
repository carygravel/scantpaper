# Spec Delta

## ADDED Requirements

### Requirement: Mnemonic-only duplicate msgids are reported once

The validation SHALL report, once over the source msgid set, each group
of msgids that become identical when keyboard-mnemonic markers are
removed, naming every member of the group. The report SHALL be advisory
and SHALL NOT fail validation.

#### Scenario: A mnemonic-only pair is reported

- **WHEN** the source msgid set contains both `Copy` and `_Copy`
- **THEN** one report names both members of the group, and validation
  exits successfully

#### Scenario: The marker may sit anywhere in the msgid

- **WHEN** the source msgid set contains `Cu_t` and `Cut`, and separately
  `Zoom _in` and `Zoom in`
- **THEN** a report is produced for each group

#### Scenario: Msgids that differ by more than a marker are not reported

- **WHEN** the source msgid set contains `Save` and `Save as…`
- **THEN** no report is produced for that pair

#### Scenario: Translations are not inspected

- **WHEN** the source defines one msgid `Copy` and a catalog translates it
  with a marker on a character the source did not mark
- **THEN** nothing is reported for that entry, because the comparison is
  between source msgids and no translation is examined
