# Design

## Context

See `proposal.md` - Why. Constraints that shape the approach:

- The packaging now asks for `debhelper-compat (= 14)`, which Ubuntu 24.04
  (the `ubuntu-latest` runner) does not provide: its debhelper is 13.x. The
  previous build failed at `mk-build-deps` for exactly that reason. Debian
  unstable has debhelper 14.5, and also provides every dependency the package
  and its tests declare - `python3-sane`, `python3-tesserocr`,
  `python3-iso639`, `python3-cysignals-bare`, `ocrmypdf` - so no PPA is
  needed there.
- `autopkgtest` needs a test source as well as the binary under test: the
  binary-only `.changes` produced by `debuild -b` carries no source, and
  `debian/tests/control` is not installed into the `.deb`. The test script
  also runs `pytest`, which needs `pyproject.toml`, `src/` and `tests/`.
- The rendered package is `Architecture: all` and pure Python, so building
  and installing it on sid is valid regardless of the Python version.
- `.gitignore` and the source tarball rule are unchanged by this work; no
  new ignored path is introduced.

## Goals / Non-Goals

**Goals:**

- Make the GitHub `.deb` prove it is lintian-clean and that its own test
  suite passes on the distribution its changelog claims.
- Build, lint and test the package on Debian unstable, so the toolchain the
  packaging requires is the toolchain that runs.
- Remove the PPA and the launchpad availability gate from the release path.
- Remove the two defects that would otherwise make the new gate fail: the
  missing screenshot and the remote images in the generated documentation.

**Non-Goals:**

- Changing the Ubuntu/PPA packaging in salsa; Ubuntu users still get their
  dependencies from the PPA at install time.
- Running autopkgtest through `unshare` or a bootstrapped rootfs, or
  reproducing Debian's archive testbed byte for byte.
- Publishing a source package or a `.dsc`; the build stays binary-only.
- Changing the test suite itself.

## Decisions

### Decision: run the build and both checks in sid containers

The build job moves into `debian:sid-slim` as well, and the launchpad
availability job disappears:

```text
build job (debian:sid-slim)             debian-checks job (debian:sid-slim)
  apt: git, ca-certificates, python3,     apt: git, ca-certificates, python3,
       build-essential, debhelper,              lintian, autopkgtest, passwd
       devscripts, fakeroot, equivs      checkout -> render (debian/tests)
  checkout -> render -> mk-build-deps    download the upload
  debuild --no-lintian                   lintian --fail-on warning
  upload .deb + .changes + .buildinfo    autopkgtest -B <deb> <tree> -- null
        |
        +------ artifact ------>
```

The two jobs stay separate even though both run in sid: the build job has
every `Build-Depends-Indep` installed, which is a superset of the test
dependencies, so autopkgtest there could not detect a missing runtime
`Depends`. A fresh container for the checks preserves that signal.

Both `debian:sid-slim` containers lack git and CA certificates, so each job
installs them before checkout; actions run inside the container. `python3` is
installed explicitly, since the renderer runs in both jobs. The container's
user differs from the workspace owner, so each job marks the checkout safe
(`git config --global --add safe.directory`) before running any git command;
without it the renderer fails with "detected dubious ownership". In the checks
job, lintian runs first so a lintian failure fails fast, before the
three-minute suite.

The checks tree is rendered and never built, deliberately: a tree that has
been through `debuild` contains the `debian/scantpaper/` staging area, and
pytest then collects the installed copy of the package alongside `src/`,
failing on `scantpaper.tests`.

### Decision: use the null testbed

The container is disposable and its base is minimal, so `-- null` is enough:
it installs the declared test dependencies and the built `.deb` from the
Debian archive and runs the suite in the container. The PPA is not needed.

Alternatives rejected:

- `unshare --release sid`: exact parity with the release procedure, but
  needs a bootstrapped or cached ~1 GB rootfs and `mmdebstrap`, which is
  more machinery than the signal is worth.
- A separate job on the ordinary GitHub runner: the runner image ships a
  broad preinstalled toolchain, which can mask a missing `Depends`. The
  container base cannot.
- Running the checks in the build job: that job has already installed every
  `Build-Depends-Indep`, a superset of the test deps, so a missing runtime
  dependency would pass unnoticed.

### Decision: upload the whole build upload

The build job uploads `scantpaper_<version>_*` - `.deb`, `.changes` and
`.buildinfo` - because linting the `.changes` reads the `.buildinfo` it
lists. Linting only the `.deb` would avoid the extra files but lose the
upload-level checks. The release step still names its asset explicitly, so
nothing extra is published.

`debuild --no-lintian` is added to the build job so the runner's lintian
does not print a second, different opinion. The sid stage is authoritative.

### Decision: run autopkgtest's tests as a normal user

Several tests in the suite inject a write failure with
`pathlib.Path.chmod(0o500)` and expect the operation to report an error. Root
ignores directory permissions, so those tests time out or see the wrong number
of callbacks when the suite runs as root - which is what `-- null` does by
default. The job therefore creates a `tester` user, makes the rendered tree
writable by it, and passes `--user tester`, so autopkgtest still installs
packages as root but runs the suite as a normal user.

This was found before pushing: in a sid container the suite failed six tests
as root and passed all 1827 as `tester`.

### Decision: install the screenshot from the source root

`debian/install` names `screenshot.png`, which is tracked and part of the
upstream tarball, so `dh_install` copies it straight from the package root.
No copy is committed under `packaging/debian/` and no `include-binaries`
entry is needed, because the packaging no longer adds a binary file.

`scantpaper.install` is deleted. With `dh-sequence-single-binary`,
`debian/install` is the file that is applied; keeping both installed the
icons, desktop file and metainfo twice. The documentation files it carried
are already covered by `scantpaper.docs`, and the screenshot moves to
`install`.

This is also the change salsa needs, for the same reason: its `uscan`
fetches GitHub's `git archive`, which contains the root `screenshot.png`.

### Decision: strip remote images when the HTML is generated

`dev/strip_remote_images.py` removes `<img>` elements whose `src` is
absolute or protocol-relative from the generated file. `debian/rules` calls
it immediately after pandoc, in `execute_after_dh_auto_build`.

Alternatives rejected:

- A lintian override: records the finding and still ships the remote
  references, which is what the check exists to prevent.
- A patch queue: the file does not exist when patches are applied, so the
  patch would have to change `README.md` - what salsa does today - which
  alters the README users and the package get, not just the generated HTML.
  This repository also rejected patch queues for packaging.
- `pandoc --self-contained`: would embed the images as data, but fetches
  them from the network during the build and defeats reproducibility.

A regex over pandoc's own output is sufficient and testable; the generated
HTML is not arbitrary input. The helper lives in `dev/`, so it ships in the
upstream tarball and salsa can call the same script.

### Decision: test the helper as a subprocess

`dev/` is not a package, so the test runs the script on a temporary HTML
file and checks the result, matching how the renderer tests invoke their
script. Cases: a remote `https` image, a protocol-relative image, and a
local image that must survive.

### Decision: verify with the local toolchain before relying on sid

The build, the strip step and lintian can all run locally. The local
lintian is older than sid's, so a clean local run is necessary but not
sufficient: the first CI run is the real gate, and it may surface new sid
tags. That is expected and is the reason for choosing sid.

## Risks / Trade-offs

- [Sid is a moving target] -> A transition in Debian can turn either job red
  without a change here. Pin the image by digest if that becomes noisy.
- [Sid's lintian is newer than the runner's] -> New tags can fire on the
  first run. Fix them, or add a justified binary override; do not disable
  the gate.
- [Building on sid changes the build toolchain, not the artifact] -> The
  package is `Architecture: all` and pure Python, and its `Depends` are
  distro package names that sid and Ubuntu both carry (or the PPA provides).
  Ubuntu users are unaffected, but a `debhelper` behaviour change in sid can
  alter the installed file layout; the lintian and autopkgtest gates catch
  that before publication.
- [The build job installs a large dependency set] -> `mk-build-deps` pulls
  every `Build-Depends-Indep` in sid. That is what the build needs; the
  checks job stays clean because it is a separate container.
- [The test suite imports the source tree, not the installed package] ->
  `pyproject.toml` sets `pythonpath = ["src"]` and the test script runs
  `pytest` in the tree, so autopkgtest verifies dependency resolution and
  test behaviour rather than the installed files byte for byte. The salsa
  test script has the same shape; fixing it is out of scope.
- [The checks job rebuilds the tree instead of downloading it] -> It must
  render from the same `source_ref`; the render is cheap and avoids a large
  artifact, but the two jobs must keep the ref expression identical.
- [The artifact now carries `.changes` and `.buildinfo`] -> Harmless: the
  release upload names the `.deb` explicitly.
- [The screenshot is installed from the root] -> If a future Debian orig
  tarball omitted `screenshot.png`, the build would fail. It is tracked, and
  no `export-ignore` exists today.

## Migration Plan

1. Add the helper and its test; change `install`, `rules`, and delete the
   unused packaging files.
2. Rewrite the workflow: upload the triple, add `--no-lintian`, move the
   build job into `debian:sid-slim`, delete the launchpad gate, and add the
   `debian-checks` job.
3. Update the packaging README, release procedure and changelog.
4. Run `pytest`, `ruff format --check`, `ruff check`, `ty check .`, render
   and build in sid, and lint the result.
5. Push the branch; the new jobs prove themselves on the pull request.
   Rollback is a revert of the change; no published asset is replaced.

## Open Questions

- Should the sid image be pinned by date or digest? Deferrable until a
  transition actually breaks a job.
