# Spec Delta

## ADDED Requirements

### Requirement: Built upload passes a lintian gate

The Debian CI SHALL lint the built upload with Debian unstable's lintian
and `--fail-on warning`, and SHALL fail the job when lintian reports a
warning or an error. Lintian SHALL be the only lintian opinion in the
workflow, so the build stage SHALL NOT run its own.

#### Scenario: Lintian runs in CI

- **WHEN** the Debian workflow runs for a push, a pull request or a
  dispatch
- **THEN** a job lints the built `.deb`, `.changes` and `.buildinfo` with
  `lintian --fail-on warning`

#### Scenario: A finding fails the job

- **WHEN** lintian reports a warning or an error for the built upload
- **THEN** the check job fails and the workflow does not publish the `.deb`

#### Scenario: The build stage does not lint

- **WHEN** the build job runs `debuild`
- **THEN** it passes `--no-lintian`, so only the Debian unstable check
  decides

### Requirement: Generated documentation references no remote resources

The built `documentation.html` SHALL NOT contain images loaded from a
remote URL, so the package neither leaks referrals nor trips lintian's
privacy checks. Local images SHALL be preserved unchanged.

#### Scenario: Remote images are removed

- **WHEN** `README.md` embeds a badge or donation image from a remote host
  and the package is built
- **THEN** the installed `documentation.html` contains no `<img>` with an
  absolute or protocol-relative source

#### Scenario: Local images are kept

- **WHEN** a documentation page references a local image
- **THEN** that image element is left untouched

#### Scenario: The privacy tags are gone

- **WHEN** the rendered documentation is linted
- **THEN** lintian reports no `privacy-breach-*` tag for it

### Requirement: Built package is tested on Debian unstable

The Debian CI SHALL run the package's own `debian/tests` against the built
`.deb` in a Debian unstable testbed, on every push and pull request, and
SHALL fail the job when a test fails. The test source SHALL come from the
rendered tree of the same source ref as the package.

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

### Requirement: Packaging installs source files by source path

A file that already exists in the source tree SHALL be installed by its
source path rather than duplicated under `packaging/debian/`, and the
packaging tree SHALL NOT declare such a file in
`debian/source/include-binaries`.

#### Scenario: Screenshot is not duplicated

- **WHEN** the package installs the project screenshot
- **THEN** `debian/install` names `screenshot.png` from the source root and
  `packaging/debian/screenshot.png` does not exist

#### Scenario: No redundant install file

- **WHEN** the packaging is built with `dh-sequence-single-binary`
- **THEN** only `debian/install` carries the package's install lines and
  there is no second per-package install file
