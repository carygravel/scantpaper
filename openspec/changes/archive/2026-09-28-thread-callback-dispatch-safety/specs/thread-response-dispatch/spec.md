## Purpose

Guarantees that a background worker's response pump keeps delivering queued
responses even when user-supplied progress or lifecycle callbacks misbehave,
so a misbehaving callback can never strand work in an indefinite "busy"
state that the user cannot escape.

## ADDED Requirements

### Requirement: Callback dispatch tolerates concurrent request registration

Dispatching the periodic progress stage SHALL tolerate requests being
registered or retired by the callbacks it invokes. A callback that cancels
its own work, registers follow-up work, or causes another request to reach a
terminal state SHALL NOT cause the dispatch pass to fail, and SHALL NOT
prevent the remaining callbacks in the same pass from running.

#### Scenario: A progress callback cancels its own request

- **WHEN** a running request's progress callback cancels that request
- **THEN** the dispatch pass completes without failing
- **AND** the cancellation is delivered to the request's cancelled callback
- **AND** the request is removed from the registry as for any other cancelled
  request

#### Scenario: A progress callback registers follow-up work

- **WHEN** a running request's progress callback registers a new request on
  the same worker
- **THEN** the dispatch pass completes without failing
- **AND** the newly registered request does not receive progress callbacks
  until it has itself started

#### Scenario: One request finishes while another is being progressed

- **WHEN** two requests are active and a progress callback for one of them
  causes the other to reach a terminal state
- **THEN** the dispatch pass completes without failing
- **AND** the remaining request still receives its progress callback

### Requirement: Response delivery survives a failing callback

A failure raised while delivering responses or progress SHALL be logged and
SHALL NOT stop the worker from delivering later responses. No failure raised
by a user-supplied callback SHALL leave the worker permanently unable to
deliver a response, because such a worker cannot report completion, report
failure, or report cancellation, and the user is left with an interface that
never finishes.

#### Scenario: A progress callback raises

- **WHEN** a running request's progress callback raises an exception
- **THEN** the exception is routed to the request's error callback
- **AND** the error callback is given the request that failed, so handlers
  that report the failing operation's name and arguments keep working
- **AND** responses queued before and after that callback are still
  delivered

#### Scenario: A terminal callback raises

- **WHEN** a request's terminal callback raises an exception
- **THEN** the worker's response delivery continues
- **AND** later requests queued on the same worker still receive their
  responses

#### Scenario: Worker stays responsive after a callback failure

- **WHEN** any callback has failed on a worker
- **THEN** a subsequent request sent to that worker still receives its
  response

### Requirement: Progress callbacks are told when there is no response

A callback invoked for periodic progress SHALL be told that no response
object is available for this pass, rather than being given a placeholder
that looks like a real response. A callback that fails while no response
object is available SHALL be routed to the request's error callback in the
same way as a callback that fails with one.

#### Scenario: Progress callback invoked without a response object

- **WHEN** a progress callback is invoked for a running request
- **THEN** it SHALL be able to distinguish that pass from one carrying a
  response object
- **AND** if it raises, the error callback SHALL be invoked

#### Scenario: A failure with no response available is still attributable

- **WHEN** a callback fails while no response object is available
- **THEN** the recorded failure SHALL name the request the callback belonged
  to
- **AND** it SHALL NOT report a process name that was never established
