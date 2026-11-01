# Spec Delta

## ADDED Requirements

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
