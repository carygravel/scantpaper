# Active Layer Selection

## Purpose

Define the single logical active layer (text or annotation) that the tabbed and
split views both represent, so that exactly one layer is selected, its editor is
shown only while its canvas is on screen, and the choice survives view switches
and restarts.

## Requirements

### Requirement: A single active layer is represented in every view mode

There SHALL be one active layer at any time: the text layer or the annotation
layer. In tabbed mode selecting the Text layer or Annotations page SHALL make
that page's layer active; selecting the Image page SHALL NOT change the active
layer, because that page shows the bare scan rather than a layer. In the split
view modes the Edit text layer / Edit annotations selection SHALL determine the
active layer.

#### Scenario: A tabbed layer page selects its layer

- **WHEN** the Text layer page is selected in tabbed mode
- **THEN** the active layer SHALL be the text layer
- **AND** when the Annotations page is selected the active layer SHALL be the
  annotation layer

#### Scenario: The image page keeps the active layer

- **WHEN** the Image page is selected in tabbed mode
- **THEN** the active layer SHALL remain whatever it was before
- **AND** the text/annotation menu selection SHALL be unchanged

#### Scenario: The edit-mode selection selects the active layer in split mode

- **WHEN** the app is in a split view mode and the user chooses Edit annotations
- **THEN** the active layer SHALL be the annotation layer
- **AND** choosing Edit text layer SHALL make the text layer active

### Requirement: Control-bar visibility follows the on-screen canvas

The active layer's control bar SHALL be shown only while that layer's canvas is
on screen: on the Text layer or Annotations page in tabbed mode, or beside the
image in a split view. The tabbed Image page SHALL show no control bar. This
SHALL hold from the moment the window is first shown, without requiring any user
action.

#### Scenario: The text layer bar is shown when the text layer is active

- **WHEN** the active layer is the text layer and its canvas is on screen
- **THEN** the text control bar SHALL be visible
- **AND** the annotation control bar SHALL be hidden

#### Scenario: The annotation layer bar is shown when annotation is active

- **WHEN** the active layer is the annotation layer and its canvas is on screen
- **THEN** the annotation control bar SHALL be visible
- **AND** the text control bar SHALL be hidden

#### Scenario: The image page hides the bar but keeps the selection

- **WHEN** the Image page is selected in tabbed mode while the text layer is
  active
- **THEN** neither control bar SHALL be visible
- **AND** the Edit text layer menu item SHALL remain selected

#### Scenario: Startup selects text but hides its bar on the image page

- **WHEN** the application starts in tabbed mode
- **THEN** the Edit text layer menu item SHALL be selected
- **AND** the Image page SHALL be shown
- **AND** neither control bar SHALL be visible until the layer's own page is
  opened

#### Scenario: A split view applies its layer at startup

- **WHEN** the application starts in a split view mode
- **THEN** the stored layer's control bar SHALL already be visible
- **AND** the user SHALL NOT have to switch to another layer and back to reveal
  it

### Requirement: The active layer is consistent across view switches

Switching between tabbed and split view modes SHALL preserve the active layer,
so the layer the user was working on stays the layer they see.

#### Scenario: Leaving tabbed mode keeps the active layer

- **WHEN** the active layer is the annotation layer in tabbed mode and the user
  switches to a split view
- **THEN** the annotation layer SHALL remain the active layer

#### Scenario: Leaving split mode lands on the matching tab

- **WHEN** the active layer is the annotation layer in a split view and the user
  switches to tabbed mode
- **THEN** the Annotations page SHALL be selected

#### Scenario: Choosing a layer from the menu in tabbed mode selects its page

- **WHEN** the app is in tabbed mode and the user chooses Edit annotations from
  the View menu
- **THEN** the Annotations page SHALL be selected
- **AND** the annotation control bar SHALL be shown

### Requirement: The active layer persists across restarts

The active layer SHALL be saved when the application exits and restored on the
next launch, so a user who was editing a layer reopens with that layer active.

#### Scenario: The active layer is restored

- **WHEN** the user leaves the annotation layer active and quits
- **THEN** the next launch SHALL restore the annotation layer as active

#### Scenario: The text layer is the default with no stored choice

- **WHEN** no active layer has been stored
- **THEN** the text layer SHALL be active on launch
