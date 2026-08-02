## Purpose

Governs the main window's scan progress bar: it is shown while a scan or device process runs, hidden when the process finishes, and hidden-and-stays-hidden when a process errors, including while modal error dialogs are open.

## ADDED Requirements

### Requirement: Progress bar hidden on process error
When a scan or device process (e.g. opening the default scanner) reports an error, the scan progress bar SHALL be hidden. While the resulting error dialog is displayed, and after it is dismissed by any of its options, the progress bar SHALL remain hidden unless a new process is started.

#### Scenario: Ignore device-open error
- **WHEN** opening the default scanner fails at application start
- **AND** the user selects the "ignore" option in the error dialog
- **THEN** the scan progress bar SHALL be hidden after the dialog is dismissed
- **AND** the progress bar SHALL NOT be visible or animated

#### Scenario: Progress bar hidden while error dialog is shown
- **WHEN** a device-open error dialog is displayed
- **THEN** the scan progress bar SHALL stay hidden for the duration of the dialog
- **AND** the progress bar SHALL NOT pulse or advance while the dialog is open

#### Scenario: Progress bar shown again on new process
- **WHEN** a new scan/device process starts after the error dialog is dismissed
- **THEN** the progress bar SHALL be shown again and report progress for that process

### Requirement: Terminal process state stops progress reporting
Once a request reaches a terminal state (error, finished, or cancelled), the background thread SHALL NOT invoke the request's running callback any further, even if callbacks for the terminal state are still being processed or a modal dialog is open.

#### Scenario: Running callback suppressed after error dispatch
- **WHEN** a request's error response is being dispatched to its callback
- **AND** the callback opens a modal dialog
- **THEN** the running callback for that request SHALL NOT be invoked while the dialog is open
- **AND** once the dialog closes, the request SHALL NOT generate any further progress updates

### Requirement: Progress bar cancel connection cleaned up on error
When a process errors, the scan progress bar's cancel-button connection SHALL be disconnected so it no longer references the process that ended.

#### Scenario: Cancel handler removed after device-open error
- **WHEN** a device-open process fails
- **THEN** the progress bar's "clicked" connection to the scan dialog's cancel action SHALL be disconnected
- **AND** a subsequent scan dialog SHALL create a fresh connection
