# debian-packaging Specification

## Purpose

Defines how scantpaper's Debian package recipe is maintained and built: it is
tracked in version control as a template, rendered into a throwaway build
tree, and leaves no `debian/` directory in the repository, so the recipe is
reviewable and reproducible while the source tree stays clean.

## Requirements

### Requirement: Debian recipe is version-controlled

The complete Debian packaging recipe SHALL be tracked under
`packaging/debian/`. The rendered `debian/` tree SHALL be a build artifact.
No workflow or script SHALL author packaging files inline, with a heredoc,
`sed` or `printf`, instead of reading them from that tree.

#### Scenario: Workflow builds the committed recipe

- **WHEN** the Debian workflow runs
- **THEN** every file in the generated `debian/` directory originates in
  `packaging/debian/`, except the changelog, which is rendered from its
  template

#### Scenario: Recipe change is reviewable

- **WHEN** a maintainer adds a build dependency to `control`
- **THEN** the change appears as an ordinary diff of
  `packaging/debian/control`, with no workflow edit

#### Scenario: Inline authoring is rejected

- **WHEN** a workflow step writes a packaging file that is not present in
  `packaging/debian/`
- **THEN** a test fails and names the unexpected file

### Requirement: Rendering happens outside the repository

The build SHALL materialise the selected ref with `git archive` into a
scratch directory below `build/`, render the `debian/` tree there, and run
the package build there. A build MUST NOT create a `debian/` directory at the
repository root.

#### Scenario: Local build leaves the checkout clean

- **WHEN** a developer renders and builds the package locally
- **THEN** the repository root contains no `debian/` directory and
  `git status` shows no new packaging files

#### Scenario: Ignore file is not changed

- **WHEN** the Debian recipe is added to the repository
- **THEN** the repository `.gitignore` contains no `/debian/` entry, so the
  source tarball imported by the salsa packaging repository cannot hide newly
  added files under its own `debian/` directory

#### Scenario: Uncommitted changes are excluded

- **WHEN** the worktree contains modified or untracked files
- **THEN** the built package is produced from the selected ref only

### Requirement: Packaging files stay native

`debian/rules` SHALL be a plain executable makefile that runs the standard dh
sequence. It MUST NOT contain renderer placeholders and MUST NOT invoke the
renderer. Every rendered file SHALL be used by unmodified Debian tooling.

#### Scenario: Rules file is executable

- **WHEN** the committed `debian/rules` template is inspected in git
- **THEN** its recorded mode is `100755`

#### Scenario: Rules file is not templated

- **WHEN** the committed `debian/rules` template is read
- **THEN** it contains no `@...@` placeholder and no call to the renderer

#### Scenario: Standard tooling needs no special flags

- **WHEN** the rendered build tree is built with `debuild -us -uc -b`
- **THEN** the build succeeds without packaging-specific options beyond
  signing and policy flags

### Requirement: Rendering is reproducible

Rendering the same commit SHALL produce byte-identical packaging on a
developer machine and in CI. No rendered packaging file SHALL depend on the
wall clock or the locale.

#### Scenario: Two renders of one commit agree

- **WHEN** the same commit is rendered twice, on different machines and
  locales
- **THEN** the rendered changelog and every other generated file are
  identical

#### Scenario: Rendered tree is buildable

- **WHEN** the renderer succeeds for a ref
- **THEN** the generated `debian/control`, `debian/changelog` and
  `debian/rules` are complete files that the Debian tools accept without
  further editing

### Requirement: CI recipe scope is documented

`packaging/debian/README.md` SHALL state that the tree builds the GitHub
release artifact and that the salsa repository remains authoritative for the
Debian and Ubuntu packages, so no reader assumes the two are kept in sync.

#### Scenario: Packager finds the authoritative tree

- **WHEN** a maintainer looks for the Debian packaging
- **THEN** `packaging/debian/README.md` names the salsa repository as the
  source of the distro package and describes the local build commands

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
