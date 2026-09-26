## Why

- openSUSE Leap 16 (the current Leap line, based on SLES 16) has no
  packaged scantpaper, and its repositories do not provide the pieces the
  Fedora build currently relies on. A full probe of a Leap 16.0 container
  (OSS, non-oss and update repos) shows that every package scantpaper needs
  that Fedora ships is missing: `python3-sane`, `python3-iso639`,
  `python3-tesserocr`, `python3-cysignals` are absent, and - unlike Fedora -
  so are `ocrmypdf`, `img2pdf`, `pdfminer.six` and `pypdf`.

- We already build, cache and validate source-built dependency RPMs for
  Fedora 43/44; extending the same mechanism to openSUSE Leap 16 gives
  users of that distribution a first-class `dnf`/`zypper` install path
  instead of an unsupported pip/wheel one.

## What Changes

- Add a `packaging/opensuse/` directory with RPM specs for the packages
  that must be built from source:
  - the four Fedora-style dependency packages: `python3-sane` (including
    the Epson `epsonscan2` `snap()` patch), `python3-tesserocr`,
    `python3-iso639`, `python3-cysignals`;
  - the missing PDF toolchain: `ocrmypdf`, `img2pdf`, `pdfminer.six` and
    `pypdf` (or whatever subset ocrmypdf's pinned requirements need);
  - `scantpaper` itself.
- Add a `.github/workflows/opensuse.yml` workflow mirroring the Fedora one
  (zypper-based steps, `opensuse/leap:16.0` container, per-package cache
  keysed on spec/patch hashes, tagged-release asset upload).
- Publish the resulting `noarch` scantpaper RPM (and the rebuilt dependency
  RPMs) as release assets alongside the Fedora ones.
- Document the openSUSE install path in `README.md` (single-transaction
  `zypper in *.rpm`, matching the Fedora instructions).
- No changes to application source, tests, or runtime behaviour.

## Capabilities

### New Capabilities

- None. This change adds build/CI and packaging infrastructure only; the
  application behaviour is unchanged, so no capability specs are produced
  (see `skip_specs: true` in `.openspec.yaml`).

### Modified Capabilities

- None.

## Impact

- **New files**: `.github/workflows/opensuse.yml`; `packaging/opensuse/`
  (seven or eight spec files + the vendored `python3-sane` patch).
- **Modified files**: `README.md` (openSUSE install section). The Fedora
  `packaging/fedora/` specs are not changed, but the two trees should stay
  in step (same sources, same patch, same `%pyproject_*` build flow).
- **Build-time dependencies introduced**: source rebuilds of `ocrmypdf`,
  `img2pdf`, `pdfminer.six` and `pypdf`, on top of the four already
  rebuilt for Fedora.
- **Platform notes**: Leap 16 ships Python 3.13 with versioned package
  names (`python313-*`) and `python3dist(...)` provides; tesserocr's
  `Cython>=3.0,<3.2` constraint is satisfied by Leap's Cython 3.0.12, so
  the Fedora 44 static-BuildRequires workaround is not needed.
- **Risk**: the `ocrmypdf` rebuild chain is the largest new cost and the
  main source of uncertainty (its pull-in of extra BRs, and version
  alignment with `pyproject.toml`'s `ocrmypdf>=15.4.3`). During
  implementation, check whether the OBS `devel:languages:python` project
  publishes Leap 16.0 builds of these packages, which would avoid those
  rebuilds.