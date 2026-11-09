# Spec Delta

## ADDED Requirements

### Requirement: Per-character Unicode mappings survive PDF/A conversion

The saved searchable text layer SHALL keep a Unicode mapping for every
character, even when text shaping would otherwise substitute a typographic
ligature for several characters.

#### Scenario: A word containing a ligature stays searchable

- **WHEN** a page's text layer contains a word whose letters could be shaped
  into a ligature, such as `ff`
- **AND** the page is saved as a searchable PDF on a system whose PDF/A
  converter drops multi-character `ToUnicode` mappings
- **THEN** the output PDF SHALL contain a searchable text layer
- **AND** extracting the text SHALL return the full word

#### Scenario: Caller-selected shaping features are preserved

- **WHEN** the text-layer renderer is asked to shape text with an explicit
  feature set
- **THEN** scantpaper SHALL leave that feature set unchanged

#### Scenario: Rendering is visually unchanged

- **WHEN** scantpaper renders the text layer without ligature substitutions
- **THEN** the visible page SHALL look the same, because the text layer is
  invisible
