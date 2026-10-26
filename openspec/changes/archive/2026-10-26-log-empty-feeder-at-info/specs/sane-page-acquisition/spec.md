# Spec Delta

## ADDED Requirements

### Requirement: A feeder-empty batch end is not reported as an error

When a scan batch ends because the driver reports that the feeder has no
documents left, the application SHALL record that as a normal end-of-batch
event at INFO level, without an exception traceback, and SHALL NOT emit an
error-level record for it. The batch SHALL still end and keep the pages
already acquired.

#### Scenario: Empty feeder ends the batch quietly

- **WHEN** the driver reports that the document feeder is out of documents
  during a scan batch
- **THEN** the application SHALL NOT emit an error-level log record or a
  traceback for that event
- **AND** it SHALL record the end of batch at INFO level
- **AND** the pages already acquired in the batch SHALL be kept

### Requirement: Genuine device errors stay errors

A scan failure that is not the feeder-empty status and not a transfer
deliberately cancelled by the user SHALL still be logged at ERROR level with
its traceback, and SHALL still be reported to the user.

#### Scenario: Device error mid-batch remains an error

- **WHEN** the driver raises an error other than the feeder-empty status
  during a scan batch, and the user has not cancelled
- **THEN** the application SHALL emit an error-level log record with a
  traceback
- **AND** the error SHALL still be reported to the user
