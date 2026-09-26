## Context

The Fedora 43/44 build (`.github/workflows/fedora.yml`) already builds,
caches (per-release, keyed on spec/patch hash) and validates four
source-built dependency RPMs (`python3-cysignals`, `python3-tesserocr`,
`python3-iso639`, patched `python3-sane`), then builds `scantpaper` itself
and uploads the RPMs as release assets. The proposals motivation and
platform probe results are in `proposal.md` - Why; key facts repeated here
for this design only:

- openSUSE Leap 16.0 is an RPM/zypper distribution with RPM 4.20, its
  default Python is 3.13 with versioned package names (`python313-*`) and
  `python3dist(...)` provides. Its `python-rpm-macros` provide the
  openSUSE `%python_*` family but **not** the Fedora `%pyproject_*`
  macros (`%pyproject_buildrequires`, `%pyproject_wheel`,
  `%pyproject_install`, `%pyproject_save_files`); this drives the unified
  pip-based build pattern in Decisions 4.
- Absent from OSS/non-oss/update: `python3-sane`, `python3-iso639`,
  `python3-tesserocr`, `python3-cysignals`, and - unlike Fedora - also
  `ocrmypdf`, `img2pdf`, `pdfminer.six`, plus the PEP 517 build backends
  `setuptools-scm` and `hatch-vcs`. `pypdf` is never needed: ocrmypdf
  16.11.1 requires `pdfminer-six`.
- Present and usable: `gtk3-devel`, `typelib-1_0-Gtk-3_0`,
  `gobject-introspection-devel`, `python313-gobject`, `python313-pycairo`,
  `python313-Pillow` (note the capital P in the package name),
  `python313-numpy`, `python313-pikepdf`, the ocrmypdf pure-Python deps
  (`rich`, `deprecation`, `pluggy`, `packaging`, `tqdm`, `cryptography`,
  `charset-normalizer`, `flit-core`, `hatchling`, `Cython`), and the tools
  (`ImageMagick`, `poppler-tools`, `tiff`, `rsvg-convert`, `qpdf`,
  `unpaper`, `djvulibre`, `xdg-utils`, `gettext-tools`, `help2man`,
  `ghostscript`, `tesseract-ocr-devel`/`tesseract-ocr`, `leptonica-devel`,
  `libcurl-devel`, `libarchive-devel`, `sane-backends-devel`/
  `sane-backends`). Cython is 3.0.12, satisfying tesserocr's
  `Cython>=3.0,<3.2` constraint.
- Two tooling gaps on Leap 16.0: `pandoc` is not packaged (the openSUSE
  `scantpaper` package ships no HTML documentation) and `tiff2ps` is
  missing (PostScript export is not offered there). Both were found in the
  container validation and are reflected in the spec files.

## Goals / Non-Goals

Goals:

- Produce installable `scantpaper` and dependency RPMs for openSUSE Leap
  16.0 via a new CI workflow, following the Fedora caching/validation
  pattern, and publish them as release assets.
- Document the openSUSE install path in README.md.

Non-goals:

- Application source changes (nothing in the app changes).
- Supporting other openSUSE lines (Tumbleweed, Leap 15.x) now; the workflow
  and cache naming keep a matrix leg possible later.
- Providing a zypper repository; release assets are plain RPM files.
- Refactoring the existing Fedora/Debian packaging.

## Decisions

1. **Separate `opensuse.yml` workflow instead of extending `fedora.yml`.**
   The two differ in package manager (`zypper` vs `dnf`), container base,
   and package names, so a matrix would bury Fedora-specific steps in both
   legs. A separate workflow keeps `fedora.yml` untouched and lets each
   distro fail/build independently. (Alternative rejected: one workflow
   with an os-dimension matrix - more readable to keep them apart.)

2. **New `packaging/opensuse/` tree derived from the Fedora specs.**
   Specs carry distro-specific names (`poppler-tools`, `tesseract-ocr-devel`,
   `python313-*`, `python3dist(...)`) and the `%{?dist}` release tag; the
   Debian and Fedora packaging already follow a per-distro-tree pattern.
   Sharing a single spec source would require macros for every difference
   with little benefit. Sources (PyPI sdist URLs), the vendored
   `python3-sane-snap-params-cache.patch`, and the build flow are shared in
   spirit and kept in step by review.

3. **Rebuild the missing Python chain from source as local packages.**
   The chain covers the pure-Python packages `img2pdf`, `pdfminer.six` and
   `ocrmypdf` plus the PEP 517 build backends `setuptools-scm` (8.2.1) and
   `hatch-vcs` (0.5.0) that Leap does not ship. `pypdf` is not built (see
   Context). ocrmypdf is pinned to 16.11.1: 17.x would additionally need
   `pypdfium2`, `fpdf2`, `uharfbuzz`, `pydantic>=2.12.5`, `pikepdf>=10`
   and `pillow>=12`, none of which exist on Leap. Its runtime
   `pi-heif` requirement is deliberately dropped - Leap provides
   `pillow_heif` and ocrmypdf imports it inside a `try/except` fallback -
   which is why ocrmypdf is the one spec with static BuildRequires. Each
   package is a cached build in dependency order (cysignals ->
   setuptools-scm -> hatch-vcs -> tesserocr -> iso639 -> sane ->
   pdfminer.six -> img2pdf -> ocrmypdf) so scantpaper's
   `python3dist(...)` requirements resolve at install time. During
   implementation, check the OBS `devel:languages:python` project for
   prebuilt Leap 16.0 rpms as an optional shortcut (see Open Questions);
   the design does not depend on it.

4. **Unified pip-based build pattern (`%pyproject_*` macros do not exist on
   openSUSE).** All openSUSE specs build wheels with
   `python3 -m pip wheel --no-deps --no-build-isolation --wheel-dir
   dist/build .` and install them with
   `pip install --root %{buildroot} --prefix %{_prefix} --no-deps
   --no-index --no-warn-script-location dist/build/*.whl`. Using
   `pip --no-build-isolation` (rather than `python3 -m build
   --no-isolation`) ignores the project's build-system-requires list, which
   `build`'s dependency checker trips over for pdfminer.six. Each spec can
   declare static BuildRequires with the Backend packages it needs
   (`python313-Cython`, `python313-hatchling`, `python313-flit-core`, ...).
   The file list is generated from the install tree:
   `find %{buildroot} \( -type f -o -type l \) -printf '/%%P\n' >
   %{_builddir}/%{name}-files.list`, consumed by `%files -f`. Version
   hooks are pinned with `SETUPTOOLS_SCM_PRETEND_VERSION=%{version}`
   (pdfminer.six, ocrmypdf). `%check` runs from `/` so the buildroot
   package shadows the source tree (whose compiled extensions/tests would
   otherwise be imported once cwd precedes PYTHONPATH). Spec comments must
   not contain `%macro`-looking tokens, because rpm expands macros even
   inside comments. tesserocr links `-lcurl`/`-larchive` directly, so it
   additionally BuildRequires `libcurl-devel` and `libarchive-devel`;
   Fedora's `%generate_buildrequires`/`%pyproject_buildrequires` are not
   used.

5. **Fetch sources with `curl` from the resolved spec, not `spectool`.**
   `spectool` (from `rpmdevtools`) is not packaged on openSUSE. Each build
   step reads the resolved `Source0:` URL from `rpmspec -P
   ~/rpmbuild/SPECS/<spec>` (a plain `grep`+`eval` breaks: `Source0:` lines
   are indented, so `eval "url=<ws>https://..."` splits into an assignment
   plus a command word) and downloads it with `curl` into
   `~/rpmbuild/SOURCES/`. The sane patch is copied from the repo checkout
   into `SOURCES/`. openSUSE's rpm `_topdir` defaults to `/usr/src/packages`,
   so the workflow writes `%_topdir <HOME>/rpmbuild` to `~/.rpmmacros` to
   match the Fedora layout.

6. **Per-package cache, keyed on spec/patch hashes, with a future-friendly
   header.**
   Mirrors `fedora.yml` exactly (`actions/cache@v6`, restore whole-package
   dirs, assemble into `~/rpmbuild/RPMS/<arch>` via
   `rpm -qp --qf '%{ARCH}'`, guard builds with `cache-hit`) but keyed
   `opensuse-${{ runner.os }}-<pkg>-<hash>`. One target (16.0) for now; an
   `os`/`leap` matrix dimension can be added later without restructuring.

7. **Resolve the release/dist tag in the container.**
   The Leap 16.0 image has no `distribution-release` package (so `%{?dist}`
   is empty). The workflow writes `%dist .lp160.1` to
   `/usr/lib/rpm/macros.d/macros.dist` so `Release: 1%{?dist}` expands to a
   deterministic `.lp160.1` tag and the built RPMs have a stable NEVRA for
   caching.

8. **Install local RPMs with zypper flags zypper actually accepts.**
   Local (unsigned, freshly built) RPMs are installed with
   `zypper -n install --allow-unsigned-rpm --force-resolution <rpms>`:
   `--allow-unsigned-rpm` is required for unsigned local files and
   `--force-resolution` lets the solver pick a repo-consistent Pillow build
   when Leap's several repositories drift between rebuilds. Options are
   only recognized after the subcommand (`zypper -n --no-recommends
   install` is rejected with "flag is not known"), which is why the
   workflow keeps the base distro installs as
   `zypper -n --gpg-auto-import-keys install --no-recommends ...`.

9. **Asset and artifact naming disambiguated from Fedora.**
   `name: scantpaper-opensuse-leap16` for the upload step and a
   `scantpaper-opensuse-leap16-*` release-asset prefix, since Fedora and
   openSUSE RPMs share the same file basenames.

## Risks / Trade-offs

- [ocrmypdf chain surprises (extra BRs, version pins)] -> Resolved during
  implementation: pinned ocrmypdf at 16.11.1 and dropped the unprovidable
  `pi-heif` requirement (static BuildRequires instead of generated), built
  the chain with the `pip --no-build-isolation` pattern, preinstalled
  `python3-hatch-vcs`, and validated the full `zypper install *.rpm`
  resolution in a clean container (single transaction, incl. Recommends).
- [openSUSE macro/packaging deltas (no `%pyproject_*` macros,
  `%{?dist}` empty, file-list handling, `%check` shadowing)] -> Addressed by
  pattern in Decisions 4/7; validated in the container chain that each
  `rpm -q --provides` exposes the expected `python3dist(...)` names
  (including both `pdfminer-six` and `pdfminer.six`).
- [Third-party tool/library naming at runtime] -> Confirmed in the
  container: the raw `libsane.so.1` resolves only with the `()`-suffixed
  provide, so `python3-sane` requires the `libsane1` package instead;
  `leptonica` is reached via the auto `libleptonica.so.6()` require;
  `python3-ocrmypdf` adds an explicit `Requires: tesseract-ocr`.
- [OBS shortcut unverified at design time] -> The design works without it;
  it is purely optional and flagged in tasks.

## Migration Plan

Purely additive: new `packaging/opensuse/` tree, new workflow, one README
section. No application code or existing packaging is modified, so there is
nothing to migrate or roll back; a bad workflow can be disabled or the
release assets removed without affecting Debian/Fedora users. The built
RPMs first appear on the next tagged release.

## Open Questions

- Does OBS `devel:languages:python` publish Leap 16.0 builds of `ocrmypdf`
  / `img2pdf` / `pdfminer.six`? Deferrable: implementation checks and, if
  present and current, may consume them instead of rebuilding (an
  optimization, not a change of approach). Left open as task 3.3.