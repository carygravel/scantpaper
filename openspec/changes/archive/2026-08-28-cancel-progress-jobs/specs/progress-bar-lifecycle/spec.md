## ADDED Requirements

### Requirement: Cancel button initiates job cancellation
When the cancel button on a progress bar is activated while the progress bar is reporting a running or queued process, the application SHALL cancel the reported work, with the same semantics as the background-job-cancellation capability, and SHALL hide the progress bar.

#### Scenario: Cancel button cancels reported work
- **WHEN** a progress bar has been set up via the queued callback
- **AND** the user activates the cancel button
- **THEN** the reported background job is cancelled
- **AND** the progress bar is hidden

#### Scenario: Cancel button creates a clean connection for later work
- **WHEN** the user activates the cancel button on a progress bar
- **AND** a subsequent process is started on the same progress bar
- **THEN** a fresh cancel connection is created
- **AND** activating the button again cancels the new process