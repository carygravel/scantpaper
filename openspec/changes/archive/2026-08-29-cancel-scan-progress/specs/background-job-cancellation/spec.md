## ADDED Requirements

### Requirement: Cancelled job requests notify their requester
When a background job request is dropped or interrupted by a cancel, the
requester SHALL be notified that the request was cancelled rather than
receiving no response, and a cancelled request SHALL NOT also complete as
finished or error.

#### Scenario: Queued job reports cancelled
- **WHEN** a job request is queued but has not yet started
- **AND** the user cancels the work that owns the request
- **THEN** the request's cancelled callback SHALL be invoked
- **AND** the request's finished callback SHALL NOT be invoked

#### Scenario: Interrupted job reports cancelled
- **WHEN** a running job's underlying work is interrupted by a cancel
- **THEN** the request's cancelled callback SHALL be invoked
- **AND** the partial output of the interrupted job SHALL NOT be presented
  as completed

### Requirement: Cancelled requests are cleaned from the registry
After a request is cancelled, the background thread SHALL remove the request
from its callback registry so the cancelled request leaves no lingering
state behind for later processing.

#### Scenario: No stray callbacks after cancel
- **WHEN** a request is cancelled
- **THEN** the request SHALL NOT produce further queued, started, running,
  finished, error, or data callbacks
- **AND** the request shall no longer appear in the thread's registry of
  active requests