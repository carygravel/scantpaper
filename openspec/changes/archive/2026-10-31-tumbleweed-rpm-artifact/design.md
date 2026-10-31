# Design

## Context

See `proposal.md` - Why. The current openSUSE build has one spec template,
one build driver and one CI workflow. `build.sh` rebuilds nine Python
dependencies because Leap 16 does not package them, writes `%dist .lp160.1`
into the rpm macros, and publishes the runtime set as
`scantpaper-opensuse-leap16`.

Tumbleweed already packages every runtime dependency at the same or a newer
version (verified against snapshot 20261028). Its default `python3` is 3.13,
and a 3.14 flavor is already built. The only local fix not in Tumbleweed is
the `snap()` patch in `python-sane`; upstream PR 109 is still open.

Constraints:

- The Leap artifact must remain byte-for-byte equivalent in content and
  behaviour.
- No application code or runtime dependency changes are needed.
- Tumbleweed is a rolling target: a snapshot can break a build without a
  repository change.
- `%suse_version` is 1600 on Leap 16 and 1699 on Tumbleweed (verified from
  each release's `macros.susedist`).

## Goals / Non-Goals

**Goals:**

- One build driver and one spec template serve both targets.
- Tumbleweed builds only ScantPaper and the patched `python-sane`; everything
  else comes from the Tumbleweed repositories.
- The patched `python-sane` follows the target's default Python flavor and
  keeps the distribution's unversioned capabilities.
- Leap behaviour, package set and artifact are unchanged.
- Tumbleweed publishes a distinct release asset and is built on the same
  triggers as the other package builds.

**Non-Goals:**

- Submitting ScantPaper or the `python-sane` patch to openSUSE:Factory.
- Enabling HTML documentation on Tumbleweed.
- Changing the application, its Python requirements, or the Leap workflow's
  cache chain.
- Adding a separate scheduled-only canary outside the standard triggers.

## Decisions

### Decision: one spec with a target conditional

`scantpaper.spec` keeps its template role and gains a dependency block
selected by `%if 0%{?suse_version} >= 1699`. The Leap branch keeps the
concrete `python313-*` names; the Tumbleweed branch uses the unversioned
`python3-*` provides, which resolve to Tumbleweed's default flavor.

The `%build`, `%install`, `%files` and `%check` sections are identical on
both targets, so a second spec would duplicate them and drift. A generated
spec fragment was also rejected: it would add renderer plumbing for a
handful of dependency lines. The conditional is limited to the two
dependency blocks, and a test asserts both branches are present.

The spec's comments are made target-neutral where they currently claim a
Leap-only fact (pandoc, the pythondist generator); the detailed rationale
stays in `packaging/opensuse/README.md`.

### Decision: target selection in the build driver

`build.sh` takes `TARGET=leap16` (the default) or `TARGET=tumbleweed`. An
unknown target exits before any setup or build. The target selects:

- the `ORDER` and `RUNTIME` arrays: Leap keeps the nine-package chain;
  Tumbleweed uses `(sane scantpaper)`;
- the `%dist` definition: `.lp160.1` on Leap, empty on Tumbleweed;
- whether `openSUSE:repo-non-oss` is enabled: Leap only.

`rpmname_for sane` is shared: it derives the package name from the same
Python flavor the spec is given, so the install and collect globs follow a
Tumbleweed default-Python bump without a second lookup table.

`setup` also installs the Tumbleweed runtime modules that ScantPaper's spec
declares as `BuildRequires` (`img2pdf`, `ocrmypdf`, `python-iso639` and
`tesserocr`), because `rpmbuild` does not resolve build dependencies itself.
The patched `python-sane` is installed from the local build before
ScantPaper, and the remaining modules are already in the setup toolchain.

The workflow sets `TARGET`, so a local build and CI still run the same
script. A small `--print-config`-style assertion is avoided; the target
mapping is checked by a test that invokes the driver with an invalid target
and by static assertions on the arrays.

### Decision: the sane spec takes a flavor macro

`python313-sane.spec` keeps its pip-based build but takes a `pyflavor`
macro, defaulting to `313`:

```text
%define pyflavor %{?pyflavor}%{!?pyflavor:313}
Name: python%{pyflavor}-sane
```

`build.sh` passes `--define 'pyflavor <nodots>'` to both `rpmspec -P` and
`rpmbuild`; on Tumbleweed it computes `<nodots>` from the installed
`python3`, so a default-Python bump changes the package name and its
dependencies together. Leap passes the same value explicitly.

The Tumbleweed package additionally declares `Provides: python3-sane` and
`Provides: python3dist(python-sane)`, so replacing Tumbleweed's package does
not make another package's requirement unsatisfiable. The `.0` version
suffix stays: it sorts above Tumbleweed's `2.9.2` and below a future
upstream release.

Alternative rejected: a Tumbleweed-only singlespec spec using
`%python_subpackages`. It would build the right names automatically but
adds a second sane spec, uses the `%pyproject_*` macros this tree
deliberately avoids, and ships both Python flavors when only the default is
needed.

### Decision: a separate Tumbleweed workflow

A new `.github/workflows/opensuse-tumbleweed.yml` runs on the same triggers
as the other package builds: `push`, `pull_request` and
`workflow_dispatch` with the existing `source_ref` input. A matrix inside
the existing Leap workflow was rejected: the Leap job's cache chain and
nine build steps would all need Tumbleweed conditionals, and the
Tumbleweed job would inherit the Leap cache and setup steps.

The build job runs `TARGET=tumbleweed build.sh setup`, builds and installs
the patched sane, builds and installs ScantPaper, verifies the imports, and
collects the runtime set. A dependent clean-room job installs the published
set on a fresh `opensuse/tumbleweed:latest` container and checks
`scantpaper --version` and the runtime imports. It also has a seeded
scenario that installs Tumbleweed's `python-sane` first, so the replacement
path is exercised. Unlike Leap, it does not assert that the patched package
survives a later update: on a rolling distribution that assertion is
time-dependent.

The release step uploads the Tumbleweed set as
`scantpaper-opensuse-tumbleweed`. The Leap set keeps its `.lp160.1` release
suffix, so the two asset names cannot collide; a test asserts the suffixes
differ.

### Decision: no static python3dist assertion on Tumbleweed

Leap's workflow asserts that no published RPM carries a `python3dist()`
require, because nothing on Leap provides those names. Tumbleweed's
pythondist requires generator is disabled, and the distribution provides the
names it would emit. The Tumbleweed check is therefore the clean-room
install itself: an unresolved `python3dist()` requirement fails the install.
The Leap assertion is not copied.

## Risks / Trade-offs

- **The patched sane is superseded by a Tumbleweed update.** The `.0` suffix
  only wins until `python-sane` reaches a later upstream version. Mitigation:
  upstream PR 109 is open; once it is merged and released, drop the local
  patch and the shadow package. Until then, the README states the caveat.
- **A rolling snapshot breaks the build.** Mitigation: the standard
  `workflow_dispatch` path can rebuild a release from a tag, and the failing
  step names the changed dependency; the build is not pinned to a snapshot.
- **`%suse_version >= 1699` is a proxy for Tumbleweed.** Mitigation: the
  condition is asserted in both CI images; if Tumbleweed changes its marker,
  the build fails before an artifact is published.
- **Unversioned `python3-*` names depend on Tumbleweed's provides.** All
  required names were verified in the 20261028 repository; the clean-room
  install catches a future removal.
- **The two release assets could collide if the Leap suffix changes.**
  Mitigation: a test asserts the Leap and Tumbleweed release strings differ,
  and the workflows upload to separate artifact names.

## Migration Plan

The change is additive. Leap's workflow, spec branch, package set and
artifact are unchanged. Tumbleweed gets a new workflow and a new release
asset; the first tag build publishes it. Rollback is removing the
Tumbleweed workflow and its artifact; no application or Leap packaging
change is involved. `README.md`, `packaging/opensuse/README.md` and
`release_procedure.md` gain the Tumbleweed install, rebuild and patch-caveat
sections.
