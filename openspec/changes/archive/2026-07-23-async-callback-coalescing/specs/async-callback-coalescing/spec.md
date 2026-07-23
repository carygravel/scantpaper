## ADDED Requirements

### Requirement: One-at-a-time response processing
`BaseThread.monitor()` SHALL process at most one response from the response
queue per invocation. If more responses remain in the queue after processing
one, `monitor()` SHALL schedule itself to be called again via `GLib.idle_add`.

#### Scenario: Single response processed immediately
- **WHEN** `monitor()` is called and the response queue contains one response
- **THEN** the response SHALL be processed (callback fired)
- **AND** no idle callback SHALL be scheduled

#### Scenario: Multiple responses processed one at a time
- **WHEN** `monitor()` is called and the response queue contains N responses
  (N > 1)
- **THEN** exactly one response SHALL be processed
- **AND** `GLib.idle_add(monitor)` SHALL be called to schedule the next
  processing iteration

#### Scenario: Empty queue fires running callbacks
- **WHEN** `monitor()` is called and the response queue is empty
- **THEN** running callbacks for all active requests SHALL still be executed
  (progress reporting)
- **AND** no idle callback SHALL be scheduled
- **AND** `monitor()` SHALL return `GLib.SOURCE_CONTINUE`

### Requirement: UI responsiveness between callbacks
Each response callback SHALL execute in its own main-loop iteration, allowing
GLib to process pending UI events (repaints, input handling, animations)
between consecutive callbacks.

#### Scenario: GUI remains responsive during multi-page import
- **WHEN** the worker thread queues N page-import responses rapidly
- **THEN** the GUI main loop SHALL process at least one UI event between each
  consecutive callback invocation
- **AND** no single main-loop iteration SHALL block for longer than one
  callback's execution time

### Requirement: Backward-compatible monitor entry point
`monitor()` SHALL remain callable directly (not only via `_on_readable`) and
SHALL return `GLib.SOURCE_CONTINUE` in all cases, preserving the existing
contract with `_on_readable` and tests.

#### Scenario: Direct call preserves return value
- **WHEN** `monitor()` is called directly (not from `_on_readable`)
- **THEN** it SHALL return `GLib.SOURCE_CONTINUE`

#### Scenario: Running callbacks fire on direct call
- **WHEN** `monitor()` is called directly with an empty queue
- **AND** there are active requests with `started=True`
- **THEN** the running callbacks for those requests SHALL be executed
