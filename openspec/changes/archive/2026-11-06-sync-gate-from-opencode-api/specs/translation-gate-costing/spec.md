# Spec Delta

## ADDED Requirements

### Requirement: The running OpenCode catalog is an import source

The gate sync SHALL accept the running OpenCode catalog as a source, reading
the resolved models and providers from the local OpenCode API. It SHALL import
the model id, provider id, family, release date, base URL, package, token
limits and prices. It SHALL import only OpenAI-compatible chat packages and
SHALL accept saved API responses for offline use.

#### Scenario: Default OpenCode models are imported

- **WHEN** the running catalog contains the default `opencode` provider and
  its models
- **THEN** the gate config contains releases and deployments for those models,
  including their families, base URLs, limits and prices

#### Scenario: A native package is skipped

- **WHEN** a catalog model uses a Responses or native package rather than an
  OpenAI-compatible chat package
- **THEN** that model is not imported and the compatible models are still
  available

#### Scenario: The API cannot be read

- **WHEN** the local OpenCode API is unavailable or returns unreadable JSON
- **THEN** the sync reports the failure and writes no gate config

#### Scenario: Saved responses are used offline

- **WHEN** the caller supplies saved model and provider responses
- **THEN** the sync imports the same catalog without contacting a running
  server

### Requirement: Integration credentials are resolved without reading secrets

The sync SHALL derive a deployment's credential environment variable from the
provider integration's declared environment method. It SHALL NOT read or copy
an API key, OAuth token or authorization header. A provider with only an OAuth
method SHALL be skipped unless the caller supplies an explicit key variable.

#### Scenario: An environment method is available

- **WHEN** the provider integration declares `OPENCODE_API_KEY` as an
  environment method
- **THEN** the deployment records `OPENCODE_API_KEY` as its key variable

#### Scenario: A provider is OAuth-only

- **WHEN** the provider integration offers OAuth but no environment method
- **THEN** its models are skipped and the reason is reported

#### Scenario: An explicit key variable overrides discovery

- **WHEN** the caller supplies a key variable for an OAuth-only provider
- **THEN** the deployment uses that variable name and still copies no secret

### Requirement: Imported provider headers are sent

The gate config SHALL allow optional provider headers on a deployment, and the
model client SHALL send them with its request. The sync SHALL copy provider
metadata headers from the catalog but SHALL NOT copy `Authorization`, cookie
or bearer-token headers.

#### Scenario: A provider metadata header is preserved

- **WHEN** the catalog provider declares a non-secret header such as
  `x-opencode-org-id`
- **THEN** the local deployment config records that header and the client
  sends it

#### Scenario: An authorization header is present

- **WHEN** the catalog response contains an `Authorization` or cookie header
- **THEN** the sync does not copy it into the gate config

### Requirement: Tiered prices are applied

A deployment cost SHALL support a base price and optional context tiers. Cost
calculation SHALL select the tier whose context size is the largest one not
exceeding the prompt token count, falling back to the base price. The selected
tier SHALL be recorded with the call evidence.

#### Scenario: A base price applies

- **WHEN** a call's prompt tokens are below every tier threshold
- **THEN** the base input, output and cache prices are used

#### Scenario: A context tier applies

- **WHEN** a call's prompt tokens exceed a tier threshold
- **THEN** that tier's prices are used and the tier is recorded

#### Scenario: A tier price is missing

- **WHEN** the selected tier does not define a required price
- **THEN** the call cost is unknown rather than zero
