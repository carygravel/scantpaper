# Spec Delta

## MODIFIED Requirements

### Requirement: Merge is deterministic and records the previous msgid

A maintained command SHALL regenerate the template and update catalogs in one
deterministic step. By default it SHALL update every catalog; when the user
names languages it SHALL update only those catalogs. For every changed entry it
SHALL record the previous msgid, and it SHALL NOT silently adopt a `msgmerge`
fuzzy match as a translation. A name with no matching catalog SHALL fail the
command before it writes the template or any catalog.

#### Scenario: A changed entry keeps its previous msgid

- **WHEN** the template changes the msgid of an entry that has a translation
- **THEN** the merge records the previous msgid beside the new entry

#### Scenario: A msgmerge fuzzy match is not adopted

- **WHEN** `msgmerge` proposes a fuzzy match for a new msgid
- **THEN** the merge leaves the entry fuzzy and does not clear it

#### Scenario: No language selection refreshes every catalog

- **WHEN** the merge command runs without naming any language
- **THEN** it merges every catalog under the source directory

#### Scenario: A named selection refreshes only those catalogs

- **WHEN** the merge command names a subset of languages
- **THEN** it merges those catalogs and leaves every other catalog unchanged

#### Scenario: A scoped merge matches the full merge

- **WHEN** one catalog is merged in a scoped run and another run merges all
  catalogs against the same template
- **THEN** the selected catalog is byte-identical in both runs

#### Scenario: An unknown language writes nothing

- **WHEN** the merge command names a language with no matching catalog
- **THEN** it exits non-zero, names the available languages, and leaves the
  template and every catalog unchanged

#### Scenario: A second run on unchanged inputs changes nothing

- **WHEN** the merge command runs twice with the same template and catalog
- **THEN** the second run changes no catalog
