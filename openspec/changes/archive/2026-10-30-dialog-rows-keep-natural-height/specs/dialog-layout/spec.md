# Spec Delta

## ADDED Requirements

### Requirement: Dialog rows keep their natural height

When a dialog has more height than its content needs, each row SHALL keep the
height its content requires. The surplus SHALL appear as empty space below the
last row and SHALL NOT be distributed into a frame, a checkbox, or a
label-and-control row.

#### Scenario: Scan dialog page options in a tall window

- **WHEN** the scan dialog is shown in a window taller than its
  **Page Options** page
- **THEN** the **# Pages** frame is at the natural height of its radio
  buttons and spin button
- **AND** the **Scan profiles** frame follows it immediately

#### Scenario: Scan dialog Postprocessing page in a tall window

- **WHEN** the scan dialog is shown in a window taller than its
  **Postprocessing** page
- **THEN** the rotate controls keep the natural height of their rows
- **AND** the remaining postprocessing rows follow immediately below them

#### Scenario: Clean up dialog in a tall window

- **WHEN** the Clean up dialog is shown in a window taller than its content
- **THEN** each option row keeps its natural height
- **AND** the rows do not spread apart to fill the window

#### Scenario: Preferences General options page in a tall window

- **WHEN** the Preferences dialog is shown on the **General options** page in
  a window taller than its content
- **THEN** each option row keeps its natural height
- **AND** the surplus appears below the last row

### Requirement: A short window still scrolls a notebook page

When a dialog is shorter than the content of a notebook page, the page SHALL
remain scrollable so that every row can be reached.

#### Scenario: Scrolling the scan dialog page options

- **WHEN** the scan dialog is shown in a window shorter than its
  **Page Options** page
- **THEN** the page scrolls
- **AND** the last row can be brought into view
