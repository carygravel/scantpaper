# dialog-layout Specification

## Purpose

Every dialog presents its content with a consistent outer inset and even
spacing between and within the rows it shows, so controls never touch the
window edge and adjacent widgets never touch each other.

## Requirements

### Requirement: Dialog content is inset from the window edge

The content area of every dialog SHALL be inset from the dialog's edges by a
non-zero, consistent margin, so no control touches the window border.

#### Scenario: A tool dialog opens with an inset

- **WHEN** a dialog opened from the Tools menu (Threshold, Brightness /
  Contrast, Negate, Unsharp Mask, Crop, Clean up, Split, OCR, User-defined)
  is shown
- **THEN** its content area has a non-zero margin on all four sides

#### Scenario: Every dialog shares the same inset

- **WHEN** any two dialogs are shown
- **THEN** both use the same content-area margin value

### Requirement: Dialog rows are spaced apart

Blocks appended to a dialog's content area — the page-range frame and each
option row — SHALL be separated by a consistent, non-zero vertical spacing, so
rows do not touch each other or the block above them.

#### Scenario: Rows in a multi-row dialog do not touch

- **WHEN** a dialog with more than one option row (for example Brightness /
  Contrast) is shown
- **THEN** the gap between consecutive rows is a non-zero, consistent spacing

#### Scenario: The page-range frame is separated from the first row

- **WHEN** a dialog that shows a page-range frame and an option row is shown
- **THEN** the row does not touch the frame above it

### Requirement: Widgets within a dialog row are spaced apart

Widgets placed side by side in a dialog row — a label, its control, and a unit
label — SHALL be separated by a consistent, non-zero horizontal spacing, so a
label does not touch the control beside it.

#### Scenario: A label and its spin button do not touch

- **WHEN** a dialog row with a label and a spin button (for example the
  Threshold dialog's "Ink strength") is shown
- **THEN** the gap between the label and the spin button is a non-zero spacing

### Requirement: A dialog restores its height when optional content collapses

When optional content inside a dialog expands the dialog, collapsing that
content SHALL return the dialog to the height it had immediately before the
content was expanded. The dialog SHALL keep its current width, including any
width the user set manually.

#### Scenario: Collapsing the advanced OCR options

- **WHEN** the user opens the OCR dialog, expands **Advanced Tesseract engine
  parameters**, and collapses it again
- **THEN** the dialog returns to its pre-expansion height
- **AND** its width is unchanged

#### Scenario: Restoring a manually chosen height

- **WHEN** the user resizes a dialog taller, expands optional content, and
  collapses it
- **THEN** the dialog returns to the taller height the user chose
- **AND** it does not shrink to the content's natural height

#### Scenario: Scrolled content does not resize its host dialog

- **WHEN** the user collapses the advanced OCR options in the scan dialog's
  scrolled Postprocessing page
- **THEN** the scan dialog's height is unchanged

### Requirement: The page-range frame keeps its natural height

The page-range selector SHALL NOT request vertical expansion, and its frame
SHALL remain at the natural height of its radio buttons when the containing
dialog has surplus height. Surplus height SHALL NOT be absorbed by spreading
the radio buttons apart.

#### Scenario: Page-range frame after optional content collapses

- **WHEN** a dialog containing the page-range frame returns to its
  pre-expansion height
- **THEN** the frame is at its natural height

#### Scenario: Page-range frame in a manually enlarged dialog

- **WHEN** the user enlarges a dialog containing the page-range frame
- **THEN** the frame stays at its natural height
- **AND** the radio buttons keep their normal spacing

### Requirement: Dialog action buttons are inset from the window edge

The action area of a dialog that presents separate action buttons SHALL be
inset from the dialog's edges by a non-zero, consistent margin, so the buttons
do not touch the window border. Where the dialog's content is inset, the
action area SHALL use the same inset.

#### Scenario: A tool or scan dialog's action buttons are inset

- **WHEN** a dialog opened from the Tools menu, or the scan dialog, is shown
- **THEN** its action buttons have a non-zero margin on all four sides

#### Scenario: A file chooser's action buttons are inset

- **WHEN** an open, save or import file chooser is shown
- **THEN** its action buttons have a non-zero margin on all four sides

#### Scenario: Action buttons line up with the content

- **WHEN** a dialog with an inset content area is shown
- **THEN** the action area uses the same inset value as the content area

### Requirement: Dialog action buttons are spaced apart

Consecutive action buttons in a dialog that presents separate action buttons
SHALL be separated by a consistent, non-zero spacing, so the buttons do not
touch each other.

#### Scenario: Apply and Cancel do not touch

- **WHEN** a tool dialog with Apply or OK and Cancel buttons is shown
- **THEN** the gap between the buttons is a non-zero, consistent spacing

#### Scenario: File chooser buttons do not touch

- **WHEN** a file chooser with Cancel and Open or Save buttons is shown
- **THEN** the gap between the buttons is a non-zero, consistent spacing

### Requirement: A joined message-dialog bar stays joined

A dialog whose action buttons are presented as a single joined bar SHALL keep
that presentation, with no added gap between the buttons and no added inset
around the bar.

#### Scenario: Warning, error and info dialogs keep a joined bar

- **WHEN** a warning, error or info message dialog is shown
- **THEN** its action buttons remain adjacent and joined to the dialog edge

#### Scenario: Joined buttons do not gain spacing

- **WHEN** a message dialog is shown
- **THEN** the spacing between its action buttons remains zero

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

### Requirement: Message dialog keeps its global hide control outside the list

The global hide control in a message dialog SHALL be outside the scrolling
message list and above the action buttons. It SHALL remain visible while the
message list scrolls.

#### Scenario: One message does not clip the global control

- **WHEN** a message dialog is shown with one message that can be stored
- **THEN** the global hide label and checkbox are fully visible above the
  action buttons
- **AND** they are not inside the scrolling message list

#### Scenario: Many messages do not scroll the global control away

- **WHEN** a message dialog contains more messages than fit in the visible list
- **THEN** the message list scrolls
- **AND** the global hide label and checkbox remain visible above the action
  buttons

### Requirement: Message list fills the available dialog height

The scrolling message list in a message dialog SHALL expand to the height the
dialog makes available. Its rows SHALL keep their natural height, and the list
SHALL scroll when the rows exceed the available height.

#### Scenario: A tall dialog gives the message list the surplus height

- **WHEN** a message dialog is shown taller than its header and message rows
  require
- **THEN** the scrolling message list expands into the surplus height
- **AND** the global hide control stays directly below the list and above the
  action buttons

#### Scenario: A short dialog scrolls the message list

- **WHEN** a message dialog is shown shorter than its message rows require
- **THEN** the message list scrolls
- **AND** every message row can be brought into view

#### Scenario: Message rows keep their natural height

- **WHEN** the message list has surplus height
- **THEN** each message row keeps the height its content requires
- **AND** the surplus appears as empty space below the last message row inside
  the scrolling list

### Requirement: Message dialog grid separates its columns and rows

The message dialog grid SHALL separate adjacent columns and adjacent rows by
the same non-zero spacing used between blocks in the dialog content area.

#### Scenario: Header and message columns do not touch

- **WHEN** a message dialog is shown with the Page, Process, Message type,
  Message, and Hide columns
- **THEN** each adjacent pair of columns has a non-zero gap
- **AND** the header labels and their message-row cells align within the same
  columns

#### Scenario: Message rows do not touch

- **WHEN** a message dialog contains more than one message row
- **THEN** each adjacent pair of message rows has a non-zero vertical gap

### Requirement: Message dialog leaves an unknown page cell empty

When a message has no page number, the message dialog SHALL leave that
message's Page cell empty and SHALL NOT show placeholder text such as `None`.

#### Scenario: A message has no page number

- **WHEN** a message dialog displays a message whose page is `None`
- **THEN** the Page cell for that message is empty
- **AND** a message with a page number still shows that number

### Requirement: Message text is selectable without text input

The message text in a message dialog SHALL be selectable and wrapped, and SHALL
NOT accept keyboard text input.

#### Scenario: Message text can be selected

- **WHEN** a user drags across a message
- **THEN** the text is selected and can be copied
- **AND** the message does not become an editable text field

### Requirement: Message dialog closes with a response

Closing a message dialog with Escape or the window close control SHALL return a
response and hide the dialog, so a caller waiting for the dialog does not hang.

#### Scenario: Escape closes the dialog

- **WHEN** the user presses Escape in a message dialog
- **THEN** the dialog returns a close response
- **AND** the dialog is hidden

#### Scenario: The window close control closes the dialog

- **WHEN** the user activates the message dialog's window close control
- **THEN** the dialog returns a close response
- **AND** the dialog is hidden
