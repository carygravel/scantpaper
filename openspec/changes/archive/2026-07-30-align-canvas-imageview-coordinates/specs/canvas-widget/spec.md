## MODIFIED Requirements

### Requirement: Canvas supports offset (pan)

The Canvas SHALL support an offset property that controls which portion of the scene is visible, clamped to prevent viewing outside the image bounds. The offset SHALL use the same sign convention as ImageView: a positive offset shifts the image rightward in widget space.

#### Scenario: Offset set within bounds
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset` is set to (100, 200)
- **THEN** the canvas SHALL scroll so that the image pixel (100, 200) aligns with the widget origin

#### Scenario: Offset clamped to prevent edge visibility
- **WHEN** the pixbuf size is (800, 1000)
- **AND** `offset.x` is set to -50
- **THEN** `offset.x` SHALL be clamped to 0

#### Scenario: offset-changed signal
- **WHEN** `offset` changes to a new value
- **THEN** the "offset-changed" signal SHALL be emitted with (x, y) integers

#### Scenario: Offset matches ImageView convention
- **WHEN** `Gdk.pointer_ungrab` offset is set on the ImageView
- **THEN** the same offset value SHALL produce the same image-visible-region on both widgets

## ADDED Requirements

### Requirement: Canvas zoom uses uniform scaling

The Canvas SHALL apply zoom as a uniform scale factor, without centering about the widget center. Centering of small images SHALL be handled by the offset clamping mechanism, matching ImageView behavior.

#### Scenario: Zoom does not re-center widget
- **WHEN** `zoom` is set to 2.0 at offset (0, 0)
- **THEN** image pixel (0, 0) SHALL appear at widget coordinate (0, 0)
- **AND** image pixel (100, 100) SHALL appear at widget coordinate (200, 200)
