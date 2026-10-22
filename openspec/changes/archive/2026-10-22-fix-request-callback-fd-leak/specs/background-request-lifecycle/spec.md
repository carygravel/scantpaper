## Purpose

Background requests release their per-request state when they terminate, so
long OCR, import, and post-processing sessions stay within the process's
file-descriptor limit and do not accumulate request state.

## ADDED Requirements

### Requirement: Terminal requests release their per-request resources

When a background request reaches a terminal state, whether finished, error,
or cancelled, the application SHALL release that request's PID-file
descriptor and its options and callback references by the time the terminal
callback returns. The release SHALL NOT require a cyclic garbage-collection
pass. While a request is active, its PID file SHALL remain readable by
cancellation so the spawned process can be identified and stopped.

#### Scenario: A completed OCR request releases its PID file

- **WHEN** an OCR request finishes and its finished callback returns
- **THEN** the request's PID-file descriptor SHALL be closed
- **AND** the request SHALL no longer appear in the worker's registry of
  active requests

#### Scenario: A long OCR batch does not accumulate descriptors

- **WHEN** a document of several hundred pages is OCR'd one request per page
- **THEN** each completed page's PID-file descriptor SHALL be closed before
  the next page's request starts
- **AND** the process's open-descriptor count SHALL return to its
  pre-batch baseline once the last terminal callback returns
- **AND** no `Too many open files` failure SHALL occur while the batch is
  running

#### Scenario: An active request keeps its PID file readable

- **WHEN** a request is running and the user cancels the work
- **THEN** the cancellation path SHALL still be able to read the spawned
  process ID from the request's PID file
- **AND** the PID file SHALL be released after the request's cancelled
  callback returns

#### Scenario: A replaced PID file is released

- **WHEN** a file-import request replaces the PID file created for its
  preceding file-information request
- **THEN** the superseded PID file SHALL be released
- **AND** the active import request's PID file SHALL remain readable for
  cancellation

### Requirement: Request options do not retain themselves

The options and callback graph built for a request SHALL NOT keep itself
alive after the request terminates. Once the worker removes its terminal
registry entry and returns from the terminal callback, releasing the
request's remaining references SHALL be sufficient to make the options and
callbacks unreachable, without a full garbage-collection pass.

#### Scenario: A completed request's options become unreachable

- **WHEN** a request reaches a terminal state and its terminal callback
  returns
- **THEN** the request's options dictionary SHALL NOT be kept alive by a
  callback stored inside that same dictionary
- **AND** no full garbage-collection pass SHALL be required to release it

#### Scenario: A long processing chain does not accumulate option graphs

- **WHEN** many rotate, threshold, unpaper, or user-defined requests complete
  in sequence
- **THEN** the completed requests' option graphs SHALL be released as each
  request terminates
- **AND** memory use SHALL NOT grow by one retained option graph per
  completed request

### Requirement: PID-file failures are reported without masking the cause

If creating a PID file fails, the application SHALL report the failure
through the configured error path using the callback's declared contract and
SHALL preserve the original operating-system error. It SHALL NOT raise a
callback-signature exception in place of the original failure.

#### Scenario: A PID file cannot be created

- **WHEN** creating a PID file fails because the temporary directory is not
  writable or the process has reached its descriptor limit
- **THEN** the configured error path SHALL receive the failure in the form it
  declares
- **AND** the reported message SHALL identify the temporary directory and
  retain the original operating-system error
- **AND** no `TypeError` from the error callback SHALL replace that report
