## MODIFIED Requirements

### Requirement: Canvas supports offset (pan)

The Canvas SHALL support an offset property that controls which portion of
the scene is visible, clamped to prevent viewing outside the image bounds.
The offset SHALL use the same sign convention as ImageView: a positive
offset shifts the image rightward in widget space. Clamping SHALL happen
against the canvas's live allocation: an offset pushed while the canvas has
no usable allocation (unmapped or zero-sized) SHALL be stored unclamped and
SHALL be clamped at the canvas's next allocation, never discarded.

#### Scenario: Offset set within bounds
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset` is set to (100, 200)
- **THEN** the canvas SHALL scroll so that the image pixel (100, 200)
  aligns with the widget origin

#### Scenario: Offset clamped to prevent edge visibility
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset.x` is set to -50
- **THEN** `offset.x` SHALL be clamped to 0

#### Scenario: offset-changed signal
- **WHEN** `offset` changes to a new value
- **THEN** the "offset-changed" signal SHALL be emitted with (x, y) integers

#### Scenario: Offset matches ImageView convention
- **WHEN** offset is set on the ImageView
- **THEN** the same offset value SHALL produce the same image-visible-region
  on both widgets
#### Scenario: Offset pushed while unallocated is clamped at allocation

- **WHEN** the canvas has a known page extent and is unmapped (zero allocation)
- **AND** `offset` is set to (357, 0)
- **AND** the canvas is then allocated
- **THEN** the stored offset SHALL be clamped against the new allocation at
  that allocation
- **AND** the offset SHALL NOT have been clamped to (0, 0) by the earlier push
