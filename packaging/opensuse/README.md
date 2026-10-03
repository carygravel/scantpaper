# openSUSE Leap 16 packaging

This directory builds the openSUSE Leap 16 RPMs for ScantPaper and the Python
packages it needs that are not packaged for Leap 16.

The build is driven by `build.sh`, which is the single source of truth for the
openSUSE build: the CI workflow (`.github/workflows/opensuse.yml`) calls the
same script, so a local build and a CI build behave identically.

## Layout

- `build.sh` - the build driver (setup / build / install / all / collect).
- `*.spec` - the RPM spec for each package (ScantPaper plus its unpackaged
  Python dependencies).
- `python3-sane-snap-params-cache.patch` - a local patch applied to python-sane.
  It keeps its `python3-` name even though the package is `python313-sane`,
  because the same patch is shared with the Fedora tree.

The dependency packages, in build order, are: cysignals, setuptools-scm,
hatch-vcs, tesserocr, iso639, sane, pdfminer.six, img2pdf, ocrmypdf, and
finally scantpaper. Each later package needs the earlier ones installed, which
is why `all` builds and installs in this order.

## Building locally

Run on an openSUSE Leap 16.0 machine (a container is fine) from a source
checkout:

```sh
bash packaging/opensuse/build.sh all
```

This installs the toolchain, fetches each sdist, builds and installs every
package in dependency order, and leaves the RPMs in `~/rpmbuild/RPMS/`. To
collect them into one directory:

```sh
bash packaging/opensuse/build.sh collect /tmp/rpms
```

`collect` copies everything (including the `-debuginfo`/`-debugsource` and
build-only helper packages). For a runnable set, use `collect-runtime`, which
copies only what a target system needs (no build-only helpers, no debug
packages):

```sh
bash packaging/opensuse/build.sh collect-runtime /tmp/rpms
```

The GitHub release artifact is built with `collect-runtime`, so the published
RPMs are the runtime set only.

To iterate on a single package (after `setup`, and once its dependencies are
installed):

```sh
bash packaging/opensuse/build.sh setup
bash packaging/opensuse/build.sh build ocrmypdf
bash packaging/opensuse/build.sh install ocrmypdf
```

## Install the built packages

On the target Leap 16 system, install the runtime packages in one transaction
so the dependency resolver can satisfy everything at once. Install only the
packages ScantPaper needs at run time; the build-only helper packages
(`python313-hatch-vcs`, `python313-setuptools-scm`) and the `-debuginfo` /
`-debugsource` packages can be left out:

```sh
sudo zypper install --allow-unsigned-rpm \
    scantpaper-*.rpm \
    python313-cysignals-*.rpm \
    python313-img2pdf-*.rpm \
    python313-ocrmypdf-*.rpm \
    python313-pdfminer.six-*.rpm \
    python313-python-iso639-*.rpm \
    python313-sane-*.rpm \
    python313-tesserocr-*.rpm
```

`--allow-unsigned-rpm` is the only flag needed. The RPMs are unsigned because
CI builds them without signing keys. There is deliberately no
`--force-resolution` and no `--allow-downgrade`: the set installs cleanly with
no extra zypper flags, and forcing resolution would hide a genuine conflict
rather than fix it. A plain `file conflicts` failure means two packages own
the same path; resolve it by removing the offending installed package, not by
forcing the transaction through.

Do not expand the whole `*.rpm` directory: that also installs
`python313-hatch-vcs` and `python313-setuptools-scm`, which are only needed to
*build* the other packages. They pull their own Python dependencies from the
Leap backports repositories, and a few of those (e.g. `python313-hatchling`)
can be temporarily missing from a mirror, which then aborts the entire
transaction with a 404.

## Why the specs look the way they do

These are the openSUSE-specific decisions, each hard-won during bring-up.

- **No `%pyproject_*` macros.** openSUSE's Python macros differ from Fedora's,
  and the packages are built with a plain `pip wheel`/`pip install` pair. See
  the `%build`/`%install` sections of any spec for the pattern.
- **Never put `%` macro tokens in spec comments.** rpm expands macros even
  inside comments, so a literal `%pyproject_install` in a comment is an error.
- **One package per module, named `python313-<pypi-project-name>`.** The name
  is derived from the PyPI project, not from the importable module. That is
  why `python-iso639` (which installs the `iso639` module) is packaged as
  `python313-python-iso639`. The `python3-*` names were wrong: Leap 16 builds
  Python 3.13 modules under `python313-*`, so a dependency on `python3-sane`
  asked for a package that does not exist.
- **No spec may hand-write `python3dist()` metadata, and no spec suppresses
  the pythondist dependency generator.** `python3dist(foo)` is a virtual
  provide that the generator emits from Python metadata in the buildroot.
  Nothing in Leap 16 provides it for every dependency, and the third-party
  OBS Python repositories do not provide it at all, so a package that
  *requires* one is unsatisfiable - zypper reports
  `nothing provides python3dist(...)` and refuses the transaction. Every spec
  therefore declares its dependencies by concrete `python313-*` name instead.

  No spec sets a suppression macro, because none is needed: Leap 16's
  `fileattrs/pythondist.attr` triggers the generator on a flat
  `site-packages/<name>.dist-info` *file*, but a PEP 427 wheel unpacks to a
  `<name>-<version>.dist-info/` *directory*, so the generator never fires for
  these pip-built specs. The built RPMs carry neither `python3dist()` requires
  nor provides, with or without a suppression macro - verified by rebuilding
  with the macro removed and getting identical metadata. CI asserts both
  halves of that: that no published RPM carries a `python3dist()` require, and
  that no spec reintroduces hand-written `python3dist()` metadata or a
  suppression macro.
- **A `.0` version suffix, deliberately and with no epoch.** Three packages -
  `python313-sane` (`2.9.2.0`), `python313-img2pdf` (`0.6.3.0`) and
  `python313-pdfminer.six` (`20260107.0`) - are also offered by a repository at
  the same upstream version. The rule is: *if a repository offers the package
  at the same upstream version, append a trailing segment to ours.* A trailing
  segment sorts after the same version and before any future release
  (`2.9.3` still wins), which is openSUSE's documented idiom, and it avoids an
  epoch, which the packaging guidelines discourage.
  Consequence: **`%{version}` is not the upstream version** - `2.9.2.0` is our
  `2.9.2`. Each of the three specs therefore defines `%define pkg_version` with
  the real upstream version and uses it for `Source0:` and the unpack
  directory; `%{version}` keeps the `.0`.
  This is what stops a system update from silently replacing our patched
  `python313-sane` with Leap's unpatched `2.9.2`. To go back to the
  distribution's package, remove ours and reinstall the distro one:
  `sudo zypper remove python313-sane && sudo zypper install python313-sane`.
- **Installing the set replaces same-named packages from other
  repositories.** That is intended. Our builds carry fixes the repository
  builds do not - the `snap()` patch in `python313-sane` is the important one -
  so they install as upgrades over them. The only caveat is that a machine
  whose rpmdb was left inconsistent by the earlier file-conflict bug may need
  the superseding third-party packages removed first; recover it with
  `zypper in artifacts/*.rpm`, or check for damaged files with `rpm -V
  python313-sane`.
- **The Fedora tree differs in package naming, by design.**
  `packaging/fedora/` keeps the `python3-*` names, which are correct there,
  while this tree uses `python313-*`. Do not "fix" that divergence: it is the
  packaging guidelines' requirement on openSUSE, not an oversight.
- **`%{dist}` is empty in the Leap 16 image**, so `setup` writes
  `%dist .lp160.1` to `/usr/lib/rpm/macros.d/macros.dist`.
- **openSUSE's default `_topdir` is `/usr/src/packages`.** `setup` points it at
  `~/rpmbuild` via `~/.rpmmacros`.
- **No spectool/rpmdevtools.** `build.sh` expands each spec with
  `rpmspec -P` and reads the resolved `Source0:` URL to fetch the sdist.
- **zypper flags come after the subcommand.** `zypper -n install
  --allow-unsigned-rpm artifacts/*.rpm` - options before `install` are
  rejected.
- **`%check` runs `cd /`** for the compiled-extension packages (tesserocr,
  sane) so the buildroot package shadows the source tree during import tests.
- **ocrmypdf is pinned to 16.11.1.** Newer ocrmypdf needs packages (pypdfium2,
  fpdf2, uharfbuzz, pydantic, pikepdf >= 10) that are not available for Leap
  16; `pi-heif` is dropped.
