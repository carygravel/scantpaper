# Spec Delta

## MODIFIED Requirements

### Requirement: Canvas supports hit testing

The Canvas SHALL identify which Bbox contains a given coordinate point. A
pointer click in widget coordinates SHALL be converted to image coordinates
with the same image-to-widget transform the renderer applies, including the
resolution ratio and display scale factor, so that the slice resolved by a
click is the one drawn under the pointer.

#### Scenario: Click inside a word bbox
- **WHEN** a word bbox exists at (10, 20, 100, 40)
- **AND** the point (50, 30) is tested
- **THEN** `get_bbox_at()` SHALL return that Bbox

#### Scenario: Click outside any bbox
- **WHEN** no bbox exists at the given coordinates
- **AND** point (0, 0) is tested
- **THEN** `get_bbox_at()` SHALL raise ReferenceError

#### Scenario: Click maps through the display scale factor
- **WHEN** the display scale factor is 2.0 and the resolution ratio is 1.0
- **AND** the zoom is 1.0 and the offset is (0, 0)
- **AND** a word bbox occupies image pixels (100, 100, 100, 50)
- **THEN** a widget click at (75, 62) SHALL resolve to that word

#### Scenario: Click maps through a non-square resolution ratio
- **WHEN** the resolution ratio is 0.5 and the display scale factor is 1.0
- **AND** the zoom is 1.0 and the offset is (0, 0)
- **AND** a word bbox occupies image pixels (10, 20, 30, 40)
- **THEN** a widget click at (60, 40) SHALL resolve to that word
