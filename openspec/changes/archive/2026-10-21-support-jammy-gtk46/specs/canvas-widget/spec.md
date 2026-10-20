## ADDED Requirements

### Requirement: Confidence colours retain their requested components

The colour conversion used for confidence-coloured boxes and text SHALL
preserve the requested red, green, blue and alpha components on every
supported PyGObject version. An opaque input colour SHALL remain fully opaque.

#### Scenario: Fully saturated red is preserved

- **WHEN** the canvas requests an opaque fully saturated red colour
- **THEN** the resulting colour SHALL have red 1, green 0, blue 0 and alpha 1

#### Scenario: Confidence colours remain visible on PyGObject 3.42

- **WHEN** max_color is black and min_color is red on PyGObject 3.42
- **AND** a word has confidence below min_confidence
- **THEN** the word SHALL be drawn in opaque red
- **AND** it SHALL NOT be drawn transparently
