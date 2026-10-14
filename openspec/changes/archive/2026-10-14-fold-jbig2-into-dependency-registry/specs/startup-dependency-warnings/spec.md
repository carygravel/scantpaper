## ADDED Requirements

### Requirement: Startup warning for missing dependencies

On startup the application SHALL warn the user about programs required by
its tools that are not installed, including the JBIG2 encoder (`jbig2`)
needed for JBIG2 PDF compression.

#### Scenario: JBIG2 encoder missing

- **WHEN** the application starts and the `jbig2` encoder is not installed
- **THEN** the startup warning SHALL mention that JBIG2 PDF compression
  requires jbig2

#### Scenario: JBIG2 encoder installed

- **WHEN** the application starts and the `jbig2` encoder is installed
- **THEN** the startup warning SHALL NOT mention the JBIG2 encoder
