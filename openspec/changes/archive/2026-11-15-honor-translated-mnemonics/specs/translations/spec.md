# Spec Delta

## ADDED Requirements

### Requirement: The message template names every source of a shared msgid

The message template SHALL list the source reference of each occurrence
of a msgid, including when one string appears in both Python sources and
GtkBuilder `.ui` files. Merging the per-language templates SHALL NOT
discard the references of a duplicate entry.

#### Scenario: A string used in Python and in a `.ui` file lists both

- **WHEN** the same translatable string appears in a Python module and in
  a GtkBuilder `.ui` file
- **THEN** the generated template contains one entry for it whose
  references name both the module and the `.ui` file

#### Scenario: A `.ui`-only string keeps its `.ui` reference

- **WHEN** a translatable string appears only in a GtkBuilder `.ui` file
- **THEN** its entry in the generated template references that `.ui` file

#### Scenario: Merging leaves the msgid set unchanged

- **WHEN** the per-language templates are merged into the message template
- **THEN** no msgid is added or removed by the merge, only references are
  combined
