# slice-focus-zoom Specification

## Purpose

Governs how the view zooms and centres when an editable slice is focused during
layer editing, so the focused text stays legible and fully visible, and lets the
user tune that zoom in context.

## Requirements

### Requirement: Focus zoom targets a consistent text size

When a slice is focused, the view SHALL zoom so the slice's text renders at a
consistent on-screen text height, independent of the slice's aspect ratio and of
the pane's aspect ratio, except where the fit bound requires a reduction.

#### Scenario: Short and long words on one line render at the same height

- **WHEN** the user focuses a short word such as "I" and then a long word such
  as "man" on the same line
- **THEN** both words SHALL render at the same on-screen text height

#### Scenario: Resizing the pane does not change the text height

- **WHEN** the user focuses a word at a given focus level, then resizes the
  pane and focuses the same word again, while the word still fits at the
  target
- **THEN** the word SHALL render at the same on-screen text height

#### Scenario: Switching between tabbed and split view keeps the text height

- **WHEN** the user focuses a word in the tabbed view at a given focus level,
  switches to a split view, and focuses the same word again
- **THEN** the word SHALL render at the same on-screen text height

### Requirement: The focus target comes from the containing line

The focus target SHALL be derived from the height of the line containing the
slice, using the line's recorded font size where present and otherwise the line
box measured across its rotation. When no line box contains the slice, the
target SHALL be derived from the slice's own font size or height.

#### Scenario: Glyph extents within a line do not change the size

- **WHEN** the user focuses a word with only x-height glyphs and then a word
  with ascenders and descenders on the same line
- **THEN** both words SHALL render at the same on-screen text height

#### Scenario: A hand-added slice without a line box is still legible

- **WHEN** the user focuses a slice added by hand, which has no containing line
  box
- **THEN** the view SHALL derive the target from the slice's own height
- **AND** the slice SHALL render at the configured focus text size

#### Scenario: A rotated line uses its perpendicular extent

- **WHEN** the user focuses a word on a line rotated by 90 degrees
- **THEN** the target SHALL be measured across the line's rotation
- **AND** the word SHALL render at the same text height as a word on an
  unrotated line

### Requirement: Focus zoom keeps the whole slice visible

The view SHALL NOT zoom beyond the level at which the focused slice and a
context margin fit entirely within the pane. When the legibility target would
overflow, the view SHALL zoom out just enough to keep the slice and margin
visible.

#### Scenario: A long word in a narrow pane stays fully visible

- **WHEN** the user focuses a word that is too long to fit at the configured
  focus text size in a narrow pane
- **THEN** the view SHALL reduce the zoom just enough for the word and the
  context margin to fit
- **AND** the word SHALL NOT be clipped

#### Scenario: A slice that fits is not reduced

- **WHEN** the user focuses a slice that fits at the configured focus text size
- **THEN** the view SHALL use the configured focus text size without further
  reduction

### Requirement: Every focus path uses the same zoom rule

Every path that focuses a slice SHALL apply the same focus zoom rule: clicking
a slice, the least-confident, first, previous, next and last navigation
controls, and the automatic focus after accepting, deleting, adding or
duplicating a slice.

#### Scenario: Clicking a slice zooms to the focus target

- **WHEN** the user clicks an editable slice
- **THEN** the view SHALL apply the focus zoom rule

#### Scenario: Confidence navigation zooms to the focus target

- **WHEN** the editor is sorted by confidence and the user activates a
  navigation control
- **THEN** the newly focused slice SHALL be shown using the focus zoom rule

#### Scenario: Accepting a correction zooms to the next slice

- **WHEN** the user accepts a correction and the editor focuses the next slice
- **THEN** the next slice SHALL be shown using the focus zoom rule

#### Scenario: Adding or duplicating focuses the new slice

- **WHEN** the user adds or duplicates a slice and the new slice becomes
  focused
- **THEN** the new slice SHALL be shown using the focus zoom rule

### Requirement: The focus level is adjustable in context

The text and annotation layer control bars SHALL provide a control for the
focus level without opening the Preferences dialog. Changing the level SHALL
apply immediately to the focused slice, SHALL persist in the user
configuration, and SHALL be resettable to the default. A level of 100% means
the default focus text size; lower values reduce the text size and show more
surrounding context.

#### Scenario: Lowering the level shows more context immediately

- **WHEN** a slice is focused and the user lowers the focus level
- **THEN** the focused slice SHALL be re-rendered at the lower level without
  another navigation action
- **AND** more of the surrounding page SHALL be visible

#### Scenario: The chosen level survives a restart

- **WHEN** the user sets a focus level, quits, and starts scantpaper again
- **THEN** focusing a slice SHALL use the chosen level

#### Scenario: Reset restores the default level

- **WHEN** the user resets the focus level
- **THEN** subsequent focus actions SHALL use the default text size
- **AND** 100% SHALL be shown as the current level

#### Scenario: The annotation layer uses the same level

- **WHEN** the user changes the focus level while editing the text layer and
  then focuses an annotation slice
- **THEN** the annotation slice SHALL be shown using the same focus level

### Requirement: The focus-level control opens on first activation

The focus-level control SHALL open its popover on every activation and SHALL
NOT retain an active popover while its control bar is hidden. Hiding the bar
for the inactive layer or the Image page SHALL close the popover before the
bar is hidden.

#### Scenario: First activation after the bar is shown

- **WHEN** a layer control bar that was hidden is shown again
- **AND** the user activates its focus-level control
- **THEN** the popover SHALL open on that first activation

#### Scenario: Switching away closes the popover

- **WHEN** the focus-level popover is open
- **AND** the user switches to a layer or page that hides the control bar
- **THEN** the popover SHALL close

#### Scenario: Returning does not require two clicks

- **WHEN** the popover was closed by hiding its control bar
- **AND** the bar is shown again
- **AND** the user activates the control once
- **THEN** the popover SHALL open
- **AND** the user SHALL NOT need a second activation

#### Scenario: Each layer's control is independent

- **WHEN** the text-layer popover is open
- **AND** the user switches to the annotation layer and activates its
  focus-level control
- **THEN** the text-layer popover SHALL be closed
- **AND** the annotation-layer popover SHALL open on that first activation
