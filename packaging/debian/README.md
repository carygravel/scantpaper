# Debian packaging

This directory is the recipe for the `.deb` attached to a GitHub release. It
is a **template**, not a buildable Debian source package: `debian/` has to sit
at the root of the tree being built, so these files are rendered into a
throwaway build tree instead of being built in place.

The Debian and Ubuntu packages are maintained elsewhere. The salsa repository
`git@salsa.debian.org:python-team/packages/scantpaper.git` is authoritative
for the distro package - its changelog history, patches, autopkgtest and PPA
releases. This tree is not kept in sync with it; changes to the distro package
belong in salsa, and this directory only needs to keep the GitHub artifact
building.

## Layout

- Every file mirrors the `debian/` file of the same name, so a reviewer can
  compare them directly.
- `changelog` is the only template: it carries `@VERSION@`, `@DATE@` and
  `@TEXT@`, which the renderer substitutes.
- `rules` is a plain, executable makefile. It is not rendered and does not call
  the renderer; rendering happens strictly before the package build.
- `README.md` (this file) is documentation and is not copied into the rendered
  tree.
- `watch`, `upstream/metadata` and `source/format` are only used when building
  a source package. A binary build (`debuild -b`) ignores them.
- `debian/locale`, `debian/documentation.html` and `debian/scantpaper.1` are
  produced by `debian/rules` during the build, inside the rendered tree. The
  generated `documentation.html` is passed through
  `dev/strip_remote_images.py`, which removes images loaded from other hosts
  so that lintian's `privacy-breach-*` checks stay clean.
- `install` names the project screenshot by its source path
  (`screenshot.png`) and installs it from the source root. It is not copied
  into this directory, and `source/include-binaries` has no entry for it.

## Building locally

The renderer needs full git history, because the version contains the commit
count. From the repository root:

```sh
python3 dev/prepare_deb.py --source-ref HEAD
```

It prints the rendered version and creates
`build/deb/scantpaper-<version>/`. Install the build dependencies from the
rendered control file, then build inside that tree:

```sh
version=$(python3 dev/prepare_deb.py --source-ref HEAD)
sudo mk-build-deps --install --remove \
    "build/deb/scantpaper-${version}/debian/control"
cd "build/deb/scantpaper-${version}"
debuild --no-lintian -us -uc -b
```

The package is written to `build/deb/`, one level above the build tree. Never
run `debuild` at the repository root: there is no `debian/` directory there,
and creating one is what this layout avoids.

To reproduce a published release, pass its tag:

```sh
python3 dev/prepare_deb.py --source-ref v4.0.1
```

The source tree is produced with `git archive`, so modified and untracked files
are not packaged. Commit to a scratch branch if you need to test a local edit.

The GitHub workflow (`.github/workflows/deb.yml`) builds in a
`debian:sid-slim` container and then runs the checks below against the built
package in a second, fresh container. Debian unstable is required: the
packaging asks for `debhelper-compat (= 14)`, which Ubuntu 24.04 does not
provide. Build in a `debian:sid` container if your host is older.

## Checks

Lintian runs on Debian unstable's version, with warnings treated as failures:

```sh
lintian --fail-on warning "build/deb/scantpaper_${version}_amd64.changes"
```

Autopkgtest runs the package's own `debian/tests` against the built `.deb`:

```sh
python3 dev/prepare_deb.py --source-ref HEAD --build-root build/deb-check
version=...  # the version printed by the command above
useradd -m tester
chown -R tester "build/deb-check/scantpaper-${version}"
autopkgtest --user tester -B "build/deb/scantpaper_${version}_all.deb" \
    "build/deb-check/scantpaper-${version}" -- null
```

The tree is needed as well as the `.deb`, because `debian/tests` is not
installed into the package; `-B` stops autopkgtest from rebuilding the tree and
using those binaries in place of the `.deb` under test. Use a freshly rendered
tree, as above: in a tree that has already been built, pytest also collects the
`debian/scantpaper/` staging area and fails. The tests run as a normal user
because several of them simulate write failures with `chmod`, which root would
sail through. The null testbed installs packages into the machine it runs on,
so run it in a disposable `debian:sid` container rather than on a working
system.

`debuild` runs with `--no-lintian` so that only the Debian unstable version
decides. Debian's lintian is newer than the one on most Ubuntu releases, and a
tag it reports has to be fixed or overridden in
`debian/<package>.lintian-overrides`, not suppressed with a workflow flag.

## Version scheme

Every build uses `<version>-0.<commit-count>.g<short-sha>`, for both tag and
branch builds, and the renderer takes `<version>` from `pyproject.toml` at the
selected ref. A `v<version>` tag must agree with that version or rendering
fails.

```text
within one upstream version:
  <version>-0.<earlier count>.g<sha>  <  <version>-0.<tag count>.g<tag-sha>
  <version>-0.<tag count>.g<tag-sha>  <  <version>-0.<later count>.g<sha>
below the distro package:
  <version>-0.<count>.g<sha>          <  <version>-1
```

The scheme keeps every upstream build below a distro package at revision `1`
without an epoch, makes a later snapshot sort above the tag it follows, and
gives one commit one version whether or not its tag exists. It mirrors the RPM
`Release:` field; see `packaging/fedora/scantpaper.spec`.

## Why the root has no `debian/`

`.gitignore` is tracked and ships in the source tarball, which the salsa
packaging repository imports. A `/debian/` entry there would hide every newly
added file in salsa's own packaging directory. The rendered tree lives under
`build/`, which an existing ignore rule already covers, so no rule has to be
added.

## Changing the packaging

Edit the files here. The workflow only renders them; it does not author any
packaging file itself, so a change to a dependency, a description or a build
rule is an ordinary reviewable diff in this directory.
