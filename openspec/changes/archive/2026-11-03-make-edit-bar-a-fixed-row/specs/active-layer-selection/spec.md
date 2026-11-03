# Spec Delta

## MODIFIED Requirements

### Requirement: Control-bar visibility follows the on-screen canvas

The active layer's control bar SHALL be shown only while that layer's canvas is
on screen: on the Text layer or Annotations page in tabbed mode, or beside the
image in a split view. The tabbed Image page SHALL show no control bar. This
SHALL hold from the moment the window is first shown, without requiring any user
action. When a bar becomes visible it SHALL be laid out within the window
immediately, without waiting for a window resize, and a hidden bar SHALL NOT
reserve vertical space.

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

#### Scenario: Opening a layer page lays out its bar without a resize

- **WHEN** the user selects the Text layer page from the Image page
- **THEN** the text control bar SHALL be laid out on screen immediately
- **AND** the view above SHALL give up the bar's height without waiting for a
  window resize

#### Scenario: Hiding the bar returns its space without a resize

- **WHEN** the user returns to the Image page while a control bar was shown
- **THEN** the bar SHALL be hidden
- **AND** the view above SHALL reclaim the bar's height without waiting for a
  window resize

#### Scenario: Entering a split view shows the bar without a resize

- **WHEN** the user switches from the tabbed Image page to a split view
- **THEN** the active layer's control bar SHALL be laid out on screen
  immediately
- **AND** the image and layer canvases SHALL be allocated their shares without
  waiting for a window resize
