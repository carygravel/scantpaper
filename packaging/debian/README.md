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
  produced by `debian/rules` during the build, inside the rendered tree.

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
debuild -us -uc -b
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

The GitHub workflow (`.github/workflows/deb.yml`) runs the same steps: render,
install the build dependencies from the rendered `control`, then `debuild` in
the rendered tree.

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
