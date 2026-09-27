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

To iterate on a single package (after `setup`, and once its dependencies are
installed):

```sh
bash packaging/opensuse/build.sh setup
bash packaging/opensuse/build.sh build ocrmypdf
bash packaging/opensuse/build.sh install ocrmypdf
```

## Install the built packages

On the target Leap 16 system, install the collected RPMs in one transaction so
the dependency resolver can satisfy everything at once:

```sh
sudo zypper install --allow-unsigned-rpm --force-resolution /tmp/rpms/*.rpm
```

The RPMs are unsigned because they are built locally (CI builds them without
signing keys). `--allow-unsigned-rpm` is required for that. `--force-resolution`
lets zypper resolve without interactive prompts.

## Why the specs look the way they do

These are the openSUSE-specific decisions, each hard-won during bring-up.

- **No `%pyproject_*` macros.** openSUSE's Python macros differ from Fedora's,
  and the packages are built with a plain `pip wheel`/`pip install` pair. See
  the `%build`/`%install` sections of any spec for the pattern.
- **Never put `%` macro tokens in spec comments.** rpm expands macros even
  inside comments, so a literal `%pyproject_install` in a comment is an error.
- **Concrete `python313-*` requires, not `python3dist(...)`.** Third-party OBS
  Python repos (e.g. `devel:languages:python`, paperless) build packages that
  only provide the concrete `python313-*` name, not the `python3dist(...)`
  virtual provide. Requiring `python3dist(...)` forces zypper to downgrade to
  the repo-oss build whenever one of those repos is enabled. Requiring the
  concrete name is satisfied by both, so no downgrade happens.
- **`%{dist}` is empty in the Leap 16 image**, so `setup` writes
  `%dist .lp160.1` to `/usr/lib/rpm/macros.d/macros.dist`.
- **openSUSE's default `_topdir` is `/usr/src/packages`.** `setup` points it at
  `~/rpmbuild` via `~/.rpmmacros`.
- **No spectool/rpmdevtools.** `build.sh` expands each spec with
  `rpmspec -P` and reads the resolved `Source0:` URL to fetch the sdist.
- **zypper flags come after the subcommand.** `zypper -n install
  --allow-unsigned-rpm --force-resolution` - options before `install` are
  rejected.
- **`%check` runs `cd /`** for the compiled-extension packages (tesserocr,
  sane) so the buildroot package shadows the source tree during import tests.
- **ocrmypdf is pinned to 16.11.1.** Newer ocrmypdf needs packages (pypdfium2,
  fpdf2, uharfbuzz, pydantic, pikepdf >= 10) that are not available for Leap
  16; `pi-heif` is dropped.
