# Canvas Widget — Delta

## ADDED Requirements

### Requirement: Canvas selection rectangle stays aligned with the scene

The Canvas SHALL render its selection rectangle in widget coordinates that
apply the same image-to-widget transform as the rendered scene: the pan offset
SHALL be scaled by the zoom level, so that a given selection rectangle occupies
the same widget position as the same rectangle drawn by the ImageView at any
zoom and offset.

#### Scenario: Selection aligned at zoom above 1
- **WHEN** the zoom is 2.0
- **AND** the offset is (100, 50)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position
  ((500 + 100) * 2, (300 + 50) * 2) with size (100 * 2, 40 * 2)

#### Scenario: Selection aligned at zoom 1
- **WHEN** the zoom is 1.0
- **AND** the offset is (100, 50)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position (600, 350) with
  size (100, 40), matching the ImageView

#### Scenario: Selection aligned when offset is zero
- **WHEN** the zoom is 2.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (500, 300, 100, 40)
- **THEN** the selection SHALL be rendered at widget position (1000, 600) with
  size (200, 80)

### Requirement: Canvas matches the ImageView resolution and display transform

The Canvas SHALL apply the same non-uniform image-to-widget transform as the
`ImageView`: the x axis SHALL be divided by the resolution ratio (x-resolution
over y-resolution) and both axes SHALL be divided by the display scale factor.
This SHALL apply to the OCR bounding boxes and the selection rectangle, and to
every widget-to-image coordinate conversion, so the Canvas content overlays the
scanned image exactly at any zoom, offset, resolution, and display scale.

#### Scenario: Non-square resolution ratio scales the x axis
- **WHEN** the resolution ratio is 0.5
- **AND** the zoom is 1.0 and the display scale factor is 1.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (10, 20, 30, 40)
- **THEN** the selection SHALL be rendered at widget position (20, 20) with
  size (60, 40) — x coordinates doubled, y unchanged

#### Scenario: HiDPI scale factor shrinks both axes
- **WHEN** the display scale factor is 2.0
- **AND** the resolution ratio is 1.0 and the zoom is 1.0
- **AND** the offset is (0, 0)
- **AND** a selection rectangle covers image pixels (10, 20, 30, 40)
- **THEN** the selection SHALL be rendered at widget position (5, 10) with size
  (15, 20)

#### Scenario: Widget-to-image conversion is the inverse transform
- **WHEN** the resolution ratio is 0.5 and the display scale factor is 2.0
- **AND** the zoom is 1.0 and the offset is (0, 0)
- **AND** a user drags in the widget from (10, 5) to (70, 15)
- **THEN** the resulting image-coordinate selection SHALL be (10, 10, 60, 20)

