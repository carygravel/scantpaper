# Spec Delta

## MODIFIED Requirements

### Requirement: Built package is tested on Debian unstable

The Debian CI SHALL run the package's own `debian/tests` against the built
`.deb` in a Debian unstable testbed, on every push and pull request, and
SHALL fail the job when a test fails. The test source SHALL come from the
rendered tree of the same source ref as the package. The declared test
dependencies SHALL include every tool that Debian packages and the suite
probes for, so a skip indicates a deliberately optional third-party tool
rather than a missing declaration.

#### Scenario: Autopkgtest runs in CI

- **WHEN** the Debian workflow runs for a push or a pull request
- **THEN** autopkgtest installs the built `.deb` in a Debian unstable
  environment, installs the declared test dependencies, and runs the suite

#### Scenario: A failing test fails the job

- **WHEN** a test in `debian/tests` fails
- **THEN** the check job fails and the workflow does not publish the `.deb`

#### Scenario: Tests match the package ref

- **WHEN** a dispatch builds an older tag with `source_ref`
- **THEN** autopkgtest runs the tests from that tag's rendered tree, not
  from the branch's

#### Scenario: A distribution tool is declared

- **WHEN** the suite probes for a tool that Debian packages
- **THEN** `debian/tests/control` declares it, so the test runs instead of
  being skipped

#### Scenario: A third-party tool is skipped

- **WHEN** a test depends on tooling Debian does not ship, such as the
  `openspec` CLI
- **THEN** the test skips and the coverage gate is unaffected
