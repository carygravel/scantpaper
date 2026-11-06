# Spec Delta

## Purpose

Makes machine-translation model choice cost-aware: imports model identity,
limits and token prices, records usage and spend for every gate action,
compares cost against quality, and estimates an action's cost before it runs.

## ADDED Requirements

### Requirement: Gate configuration is imported from an OpenCode config

The gate SHALL be able to generate or update its releases and deployments from
an OpenCode JSON or JSONC configuration. It SHALL import only
OpenAI-compatible providers and SHALL validate the resulting configuration
before writing it.

#### Scenario: An incompatible provider is present

- **WHEN** the OpenCode config also contains a non-OpenAI-compatible provider,
  such as an Anthropic-native package
- **THEN** that provider is not imported and the compatible providers are
  still available

#### Scenario: The result is invalid

- **WHEN** the imported releases and deployments do not satisfy the gate's
  independence rules
- **THEN** the importer refuses to write the configuration

### Requirement: Model identity, limits and prices are imported

The importer SHALL take the endpoint from the provider's base URL, the
credential from the first environment variable name, and model identity,
family, release date, token limits and prices from the model entry.

#### Scenario: An OpenAI-compatible provider is imported

- **WHEN** an OpenCode config defines an OpenAI-compatible provider with one
  model, a base URL, an environment variable, a family, a release date, token
  limits and prices
- **THEN** the gate config contains a release and deployment for that model,
  with the endpoint, environment variable, limits and prices preserved

### Requirement: Proposer and judge roles are explicit

The importer SHALL take proposer and judge roles from a separate role policy,
because the OpenCode config does not define them. It SHALL refuse a role that
does not name an imported deployment or that breaks family independence.

#### Scenario: Proposer and judge roles are missing

- **WHEN** an OpenCode config describes two or more models but the role policy
  does not name a proposer and a judge
- **THEN** the import refuses to write a gate config and reports the missing
  role

#### Scenario: The role policy is valid

- **WHEN** the role policy names two proposers from different families and a
  judge from a third family
- **THEN** the imported deployments carry those roles

### Requirement: Re-import preserves manual gate settings

A repeated import SHALL be deterministic. It SHALL preserve thresholds and
hand-edited deployment fields, including quantization, prompt hash and
decoding, unless the caller explicitly requests replacement.

#### Scenario: A second import produces no diff

- **WHEN** the importer runs twice with the same OpenCode config and role
  policy
- **THEN** the second run produces no change to the gate config

#### Scenario: A manual field is preserved

- **WHEN** a deployment has a hand-edited quantization and prompt hash
- **THEN** a normal re-import keeps those values instead of replacing them
  with defaults

### Requirement: An imported config never contains a credential

The importer SHALL copy environment variable names but SHALL NOT copy a
literal API key, bearer token or authorization header from the OpenCode
config. A provider whose credential is only a literal value SHALL be reported
and skipped.

#### Scenario: An environment variable is imported

- **WHEN** the OpenCode provider names `INFERENCE_TOKEN` in its
  environment list
- **THEN** the gate deployment records `INFERENCE_TOKEN` as its key
  variable and contains no key value

#### Scenario: A literal key is present

- **WHEN** the OpenCode provider supplies an API key as a literal string
- **THEN** the importer refuses that provider rather than writing the secret

### Requirement: Every model call records usage and cost

The gate SHALL read the usage returned by the provider for every model call
and SHALL compute a cost from the deployment's input, output and cache prices.
It SHALL record the deployment, release, token counts, latency and cost with
the call's evidence. When a provider omits usage, the gate SHALL record usage
and cost as unknown rather than inventing them.

#### Scenario: Usage is reported

- **WHEN** a provider returns prompt and completion token counts for a gate
  proposal
- **THEN** the evidence records those counts and a cost derived from the
  deployment's prices

#### Scenario: Cached tokens are priced separately

- **WHEN** the provider reports cached prompt tokens and the deployment has a
  cache-read price
- **THEN** the cached tokens are charged at the cache-read price and the rest at
  the input price

#### Scenario: Usage is missing

- **WHEN** a provider returns text without a usage object
- **THEN** the call evidence records usage as unknown and does not assign a
  cost

### Requirement: Cost and quality are compared per model

The gate SHALL produce a cost/performance report that groups calls by
language, release and deployment and reports spend, call count, tokens,
approvals, abstentions, approval rate, cost per approval, qualification and
drift scores, and the observed defect rate where available. The report SHALL
include abstentions and failed calls, not only approved strings.

#### Scenario: Two deployments are compared

- **WHEN** two qualified deployments produce approvals at different cost and
  quality
- **THEN** the report shows both deployments' spend, approval rate, cost per
  approval and available quality scores

#### Scenario: A model mostly abstains

- **WHEN** a deployment makes many calls and approves few strings
- **THEN** its abstentions and failed calls are included in its cost and
  approval-rate figures

### Requirement: An action's cost is estimated before it runs

The gate SHALL estimate the token count and cost of a qualification, drift
probe or gate action before making any request. The estimate SHALL be based on
the actual source or probe strings, the configured maximum output tokens and a
documented character-to-token heuristic. It SHALL report a range per
deployment and SHALL state that provider-reported usage after the action is
authoritative.

#### Scenario: A gate batch is estimated

- **WHEN** a maintainer asks for the cost of gating a set of strings
- **THEN** the estimate reports input tokens, output tokens and cost per
  proposer, judge and back-translation deployment

#### Scenario: A qualification is estimated

- **WHEN** a maintainer asks for the cost of qualifying a release for a
  language
- **THEN** the estimate uses the held-out baseline size and the release's
  model limits

#### Scenario: A probe is estimated

- **WHEN** a maintainer asks for the cost of a drift probe
- **THEN** the estimate uses the number of probe items and the named
  deployment

### Requirement: A budget stops an action before it spends

The gate SHALL accept a maximum cost for an action and SHALL refuse to make
any request when the pre-action estimate exceeds it. The refusal SHALL name
the estimate, the budget and the deployments that exceed the budget.

#### Scenario: The estimate is within budget

- **WHEN** the estimated cost is below the configured maximum
- **THEN** the action proceeds

#### Scenario: The estimate exceeds budget

- **WHEN** the estimated cost is above the configured maximum
- **THEN** no model request is made and the action exits non-zero with the
  estimate and budget in the message
