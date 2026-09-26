# Tasks: add openSUSE Leap 16 RPM builds

## 1. Packaging spec files

- [x] 1.1 Create `packaging/opensuse/` with `python3-cysignals.spec`
      (adapted from Fedora: `python313-*` BuildRequires, `python3dist(...)`
      references, no `python3.14dist` naming).
- [x] 1.2 Create `packaging/opensuse/python3-iso639.spec` (same adaptations).
- [x] 1.3 Create `packaging/opensuse/python3-tesserocr.spec` keeping
      `%generate_buildrequires`/`%pyproject_buildrequires` (Leap Cython
      3.0.12 satisfies the constraint, so no Fedora-44 static-BR
      workaround). Verified the generated requires resolve on Leap.
      REWORKED: openSUSE's `python-rpm-macros` provide no `%pyproject_*`
      macros (Fedora-only), so all openSUSE specs use a common
      pip-based pattern instead (see 1.11) with static BuildRequires.
      tesserocr links `-lcurl`/`-larchive` directly, so it needs
      `libcurl-devel` and `libarchive-devel` BuildRequires; its explicit
      `Requires: leptonica` was dropped (the runtime lib resolves via
      `libleptonica.so.6()`).
- [x] 1.4 Create `packaging/opensuse/python3-sane.spec` and copy the
      vendored `python3-sane-snap-params-cache.patch`; same source as the
      Fedora tree.
- [x] 1.5 Create `packaging/opensuse/python3-img2pdf.spec` (pure-Python,
      build via `%pyproject_*` macros, `python313-flit-core`
      BuildRequires). REWORKED: uses the shared pip-based build pattern
      (1.11) with `python313-flit-core` as the build backend.
- [x] 1.6 Create `packaging/opensuse/python3-pdfminer.six.spec` (pure-Python
      build; provides both `python3dist(pdfminer.six)` and
      `python3dist(pdfminer-six)`).
- [x] 1.7 pypdf NOT needed: ocrmypdf 16.11.1's requirements use
      `pdfminer-six`, not `pypdf`; the spec was dropped. `setuptools-scm`
      and `hatch-vcs` (build backends absent from Leap) were added as
      `python3-setuptools-scm.spec` and `python3-hatch-vcs.spec` instead.
- [x] 1.8 Create `packaging/opensuse/python3-ocrmypdf.spec` pinned to
      16.11.1 (the newest ocrmypdf whose every dependency exists on Leap
      16.0; 17.x would additionally need pypdfium2/fpdf2/uharfbuzz/pydantic
      and pikepdf/pillow rebuilds). Img2pdf/pdfminer.six built before it,
      static build requires because of the intentionally dropped `pi-heif`
      runtime requirement (Leap ships `pillow_heif`, not `pi_heif`).
- [x] 1.9 Create `packaging/opensuse/scantpaper.spec`, adapted from the
      Fedora one: `python313-*`/openSUSE names, `poppler-tools` instead of
      `poppler-utils`, `tesseract-ocr-devel`/`leptonica-devel`,
      `rsvg-convert` instead of `librsvg2`, `tiff` instead of
      `libtiff-tools`, `gettext-tools`, no pandoc (not packaged on Leap),
      plus the explicit runtime `Requires:`/`Recommends:` for the
      subprocess tools.
- [x] 1.10 Verify every spec parses cleanly: `rpmspec -P` exit 0 on Leap
       16.0 for all 10 specs; `Release: 1%{?dist}` expands to `1.lp160.1`
       with the workflow-defined dist macro; sources resolve to the pinned
       sdists.
- [x] 1.11 No Fedora-style `%pyproject_*` macros on openSUSE; all specs
       instead use a unified pattern: a `%build` that runs
       `python3 -m pip wheel --no-deps --no-build-isolation
       --wheel-dir dist/build .` (this ignores the PEP 517
       build-system-requires list, which `python3 -m build --no-isolation`
       chokes on for pdfminer.six), a `%install` that runs
       `pip install --root %{buildroot} --prefix %{_prefix} --no-deps
       --no-index --no-warn-script-location dist/build/*.whl` and writes
       a file list with `find %{buildroot} \( -type f -o -type l \)
       -printf '/%%P\n' > %{_builddir}/%{name}-files.list`, and
       `%files -f %{_builddir}/%{name}-files.list`. Version hooks are
       pinned with `SETUPTOOLS_SCM_PRETEND_VERSION=%{version}` (pdfminer
       .six, ocrmypdf). %check runs from `/` so the installed package
       shadows the source tree. Spec comments must not contain `%macro`
       tokens (rpm expands macros even in comments).

## 2. CI workflow

- [x] 2.1 Create `.github/workflows/opensuse.yml`, mirroring the Fedora
      cache/build pattern: `opensuse/leap:16.0` container, enable the
      preconfigured non-oss repo (fresh Leap 16 images have no usable
      separate update repos), install base build tools (gcc, gcc-c++,
      make, pkgconf-pkg-config, rpm-build, python-rpm-macros,
      python3-base, python313-devel/setuptools/pip/wheel/Cython/build/
      flit-core/hatchling/packaging, curl) and all runtime tool deps
      (python313-pillow/pikepdf/gobject/pycairo/numpy/Pillow (note the
      capital P in the package name)
      gtk3-devel, typelib-1_0-Gtk-3_0, gobject-introspection-devel,
      tesseract-ocr-devel/tesseract-ocr, leptonica-devel,
      sane-backends-devel/sane-backends, ghostscript, poppler-tools,
      rsvg-convert, tiff, ImageMagick, qpdf, unpaper, djvulibre,
      xdg-utils, gettext-tools, help2man, and the python313-ecosystem
      runtime deps rich/pluggy/deprecation/tqdm/polib/pytest/
      cryptography/charset-normalizer).
- [x] 2.2 Define `%{?dist}` as `.lp160.1` by writing
      `/usr/lib/rpm/macros.d/macros.dist`: Leap 16 ships no
      `distribution-release`/`openSUSE-release` package in the repos, so
      the macro is otherwise empty.
- [x] 2.3 Add per-package restore/build/install steps in dependency order
      (cysignals -> setuptools-scm -> hatch-vcs -> tesserocr -> iso639 ->
      python3-sane -> pdfminer.six -> img2pdf -> ocrmypdf), each guarded
      by its `opensuse-${{ runner.os }}-<pkg>-<spec+patch hash>` cache and
      fetching sources by reading `Source0:` from the spec with `curl`
      (spectool/rpmdevtools are not packaged on Leap). Sources are read
      from the resolved spec with `rpmspec -P` (not grep/eval, which
      splits on the leading whitespace); `%_topdir` defaults to
      `/usr/src/packages` on openSUSE so it is pointed at `$HOME/rpmbuild`;
      the sane patch is copied from the repo checkout; local RPM installs
      use `zypper -n install --allow-unsigned-rpm --force-resolution`
      (option-only-after-subcommand parsing).
- [x] 2.4 Add the `scantpaper` build step (curl-from-Source0 fetch, same
      as the dependency steps) plus `rpm -q` verification of the resulting
      toolchain, artifact upload under the `scantpaper-opensuse-leap16`
      name, and `softprops/action-gh-release` upload on tags.

## 3. Container validation

- [x] 3.1 Run the full chain in a local `opensuse/leap:16.0` container:
      all dependency RPMs build from source, tesserocr builds with Cython
      3.0.12, and `rpm -q --provides` shows `python3dist(...)` names (not
      `python3.14dist`). Final run exit 0: all 10 rpms built and
      installed, `import sane, tesserocr, iso639, img2pdf, ocrmypdf,
      scantpaper` succeeds, `python3dist(pdfminer-six)` and
      `python3dist(pdfminer.six)` are both provided.
- [x] 3.2 Validate `scantpaper` RPM resolves its `Requires:` and
      `Recommends:` on Leap 16.0 (single-transaction `zypper in *.rpm`
      in a clean container; `--allow-unsigned-rpm --force-resolution`
      needed for unsigned local rpms and Leap's multi-repo Pillow build
      drift); confirm the installed app imports and reports a sane
      version. Done: 198 packages installed, all imports OK, ocrmypdf
      16.11.1.
- [ ] 3.3 Check OBS `devel:languages:python` for prebuilt Leap 16.0
      `ocrmypdf`/`img2pdf`/`pdfminer.six`/`pypdf` rpms; if current, note
      them as an install-time alternative to the local builds (optional,
      does not change the workflow).

## 4. Documentation

- [x] 4.1 Add an openSUSE Leap 16 install section to `README.md`
      (single-transaction `zypper in *.rpm` from the release assets,
      matching the Fedora wording; lines stay <= 80 columns).
      Notes the unsigned RPMs, the locally rebuilt `python3dist(...)`
      packages, and that PostScript export is unavailable (no `tiff2ps`
      on Leap 16.0).

## 5. Quality gates and release

- [x] 5.1 Confirm the change is touching no application source or tests:
      `pytest`, `ruff check .` and `ty check .` remain green and unchanged.
      Verified: 1263 passed, 3 xfailed, coverage 99.28%; `ruff check .`
      and `ruff format --check .` clean; `ty check .` clean.
- [x] 5.2 Push the workflow branch and confirm a PR run builds all RPMs
      with cache hits on re-run; verify a tag run attaches
      `scantpaper-opensuse-leap16-*` assets. Confirmed green upstream
      (built all openSUSE RPMs; the scantpaper verify step now installs
      the package first).