# Spec Delta

## ADDED Requirements

### Requirement: Synthetic line grouping preserves word geometry

When a flat text layer with no line structure is wrapped into synthetic
`ocr_line` elements for saving, words SHALL be grouped so that one word's
size cannot distort another word's rendering. A tall word (such as a
rotated slice) SHALL NOT pull upright words that sit on different rows
into a single synthetic line, because the renderer derives a line's font
size from its bounding box.

#### Scenario: Mixed-angle flat layer keeps upright rows separate

- **WHEN** a flat text layer contains upright words across several rows
  and at least one rotated word taller than an upright word
- **AND** the page is saved as a searchable PDF
- **THEN** the upright words SHALL be grouped into one synthetic line per
  row
- **AND** each upright word SHALL be rendered at a height comparable to its
  own bounding box rather than the taller rotated word's

#### Scenario: Equal-height words on one row still share a line

- **WHEN** a flat text layer contains upright words whose vertical centres
  are aligned on one row
- **THEN** those words SHALL be grouped into a single synthetic line
- **AND** that line's bounding box SHALL enclose only those words

#### Scenario: Spaced rotated words each keep their own line

- **WHEN** a flat text layer contains rotated words spaced apart along
  their reading direction
- **THEN** each rotated word SHALL form its own synthetic line
- **AND** each such line SHALL carry the word's text angle
