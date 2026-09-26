Name:           scantpaper
Version:        3.0.19
Release:        1%{?dist}
Summary:        GUI to produce PDFs or DjVus from scanned documents

License:        GPL-3.0-only
URL:            https://github.com/carygravel/scantpaper
Source0:        https://github.com/carygravel/scantpaper/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build

# Native/system dependencies needed at runtime.
BuildRequires:  gtk3-devel
BuildRequires:  typelib-1_0-Gtk-3_0
BuildRequires:  gobject-introspection-devel
BuildRequires:  pkgconf-pkg-config
BuildRequires:  python313-gobject
BuildRequires:  python313-pycairo
# The Python dependencies are the locally built packages; python3dist
# provider names are resolved by the generated auto-requires.
BuildRequires:  python3-tesserocr
BuildRequires:  tesseract-ocr-devel
BuildRequires:  leptonica-devel
BuildRequires:  python3-ocrmypdf
BuildRequires:  python3-img2pdf
BuildRequires:  python3-sane
BuildRequires:  python3-iso639
BuildRequires:  python3dist(pillow)
BuildRequires:  python3dist(pikepdf)

# Tools used to generate the additional files installed by the package.
BuildRequires:  gettext-tools
BuildRequires:  help2man
BuildRequires:  python313-polib
# openSUSE Leap 16 does not ship pandoc, so the HTML documentation is
# intentionally not generated on this distribution (Fedora does).

# Runtime dependencies which are also needed while generating documentation
# and testing the resulting installation.
BuildRequires:  ImageMagick
BuildRequires:  tiff
BuildRequires:  poppler-tools
BuildRequires:  rsvg-convert
BuildRequires:  ghostscript

# Python runtime dependencies are generated automatically from pyproject.toml.
# The tools invoked via subprocess (convert, tiffcp, pdfunite, rsvg-convert,
# gs, and the Recommends below) are not covered by the Python METADATA
# auto-requires, so they are declared explicitly:
Requires:  ImageMagick
Requires:  tiff
Requires:  poppler-tools
Requires:  rsvg-convert
Requires:  ghostscript

# TIFF-to-PostScript conversion (tiff2ps) is not packaged on openSUSE Leap
# 16 (libtiff 4.7 dropped tiff2ps); the "save as PS" path degrades with an
# error dialog rather than being offered.
Recommends: djvulibre
Recommends: qpdf
Recommends: tesseract-ocr
Recommends: unpaper
Recommends: xdg-utils

# GTK runtime pieces that the Python introspection bindings need.
Requires:  libgtk-3-0
Requires:  typelib-1_0-Gtk-3_0

%description
ScantPaper is a GUI application for scanning documents and producing
PDF, DjVu, TIFF, PS, TXT, hOCR, SDB and image files.

It uses SANE for scanner access and provides tools for editing scanned
pages, OCR, metadata handling and PDF/DjVu generation.

%prep
%autosetup -n scantpaper-%{version}

%build
# Generate the wheel with setuptools (see the dependency specs for why pip
# rather than unavailable PEP 517 macros).
python3 -m pip wheel \
    --no-deps \
    --no-build-isolation \
    --wheel-dir dist/build \
    .

# Generate gettext message catalogs.
python3 dev/compile_mo.py \
    --src po \
    --out locale \
    --domain scantpaper

%install
python3 -m pip install \
    --root %{buildroot} \
    --prefix %{_prefix} \
    --no-deps \
    --no-index \
    --no-warn-script-location \
    dist/build/*.whl

# Install compiled translations.
mkdir -p %{buildroot}%{_datadir}/locale
cp -a locale/. %{buildroot}%{_datadir}/locale/

# Desktop entry.
install -Dpm 0644 \
    org.scantpaper.desktop \
    %{buildroot}%{_datadir}/applications/org.scantpaper.desktop

# AppStream metadata.
install -Dpm 0644 \
    org.scantpaper.desktop.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/org.scantpaper.desktop.metainfo.xml

# Icons.
mkdir -p %{buildroot}%{_datadir}/icons
cp -a src/scantpaper/icons/* %{buildroot}%{_datadir}/icons/

# Documentation.
install -Dpm 0644 \
    README.md \
    %{buildroot}%{_docdir}/%{name}/README.md

# Generate the man page in the same way as the Debian package.
mkdir -p %{buildroot}%{_mandir}/man1

help2man \
    --no-info \
    --name='a GUI to produce PDFs or DjVus from scanned documents' \
    --version-string=%{version} \
    --output=%{buildroot}%{_mandir}/man1/scantpaper.1 \
    'PYTHONPATH=src python3 -m scantpaper.app'

sed -i \
    -e 's/APP.PY/SCANTPAPER/' \
    -e 's/app.py/scantpaper/' \
    %{buildroot}%{_mandir}/man1/scantpaper.1

# Write the file list last, so it covers every file installed above (the
# pip wheel plus the translations, desktop entry, AppStream metadata,
# icons, README and man page). The man page is excluded: rpm compresses it
# to .gz during packaging, so it is declared explicitly with a wildcard.
# The list is the single source for %files, and further explicit %files
# entries would only duplicate paths.
find %{buildroot} \( -type f -o -type l \) \
    -not -name 'scantpaper.1' \
    -printf '/%%P\n' \
    > %{_builddir}/%{name}-files.list

%check
# The upstream test suite needs a graphical environment, so don't run it
# here yet. The GitHub Actions workflow should run the tests separately
# under Xvfb.

# Everything installed in %install (the Python wheel plus the translations,
# desktop entry, AppStream metadata, icons, README) is captured by the
# find-generated file list written at the end of %install; only the man page
# is declared here, with a wildcard to cover the .gz compression rpmlint's
# brp-compress applies during packaging.
%files -f %{_builddir}/%{name}-files.list

%{_mandir}/man1/scantpaper.1*

%changelog
* Sun Sep 20 2026 Jeffrey Ratcliffe <jffry@posteo.net> - 3.0.19-1
- Initial openSUSE RPM package (pandoc HTML documentation dropped;
  pandoc is not packaged on Leap 16)