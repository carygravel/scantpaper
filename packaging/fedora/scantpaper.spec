Name:           scantpaper
Version:        3.0.19
Release:        1%{?dist}
Summary:        GUI to produce PDFs or DjVus from scanned documents

License:        GPL-3.0-only
URL:            https://github.com/carygravel/scantpaper
Source0:        https://github.com/carygravel/scantpaper/archive/refs/tags/v%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  pyproject-rpm-macros

# Native/system dependencies needed at runtime.
BuildRequires:  gtk3
BuildRequires:  python3-gobject
BuildRequires:  python3-cairo
# python3dist(python-sane) is satisfied by the locally built python3-sane
# package (see python3-sane.spec), which also carries the snap() fix for
# backends such as Epson epsonscan2.
BuildRequires:  python3-tesserocr
BuildRequires:  tesseract-devel
BuildRequires:  leptonica-devel

# Tools used to generate the additional files installed by the Debian package.
BuildRequires:  gettext
BuildRequires:  pandoc
BuildRequires:  help2man
BuildRequires:  python3-polib

# Runtime dependencies which are also needed while generating
# documentation/manpage and while testing the resulting installation.
BuildRequires:  ImageMagick
BuildRequires:  libtiff-tools
BuildRequires:  poppler-utils
BuildRequires:  ocrmypdf

# Python runtime dependencies are generated automatically from pyproject.toml.
# The tools invoked via subprocess (qpdf, convert, tiffcp, unpaper, ...) are
# not covered by the Python METADATA auto-requires, so they are declared
# explicitly, mirroring the Debian package's dependency lists:
Requires:  ImageMagick
Requires:  libtiff-tools
Requires:  librsvg2
Requires:  poppler-utils
Recommends: djvulibre
Recommends: qpdf
Recommends: tesseract
Recommends: unpaper
Recommends: xdg-utils

%description
ScantPaper is a GUI application for scanning documents and producing
PDF, DjVu, TIFF, PS, TXT, hOCR, SDB and image files.

It uses SANE for scanner access and provides tools for editing scanned
pages, OCR, metadata handling and PDF/DjVu generation.

%generate_buildrequires
%pyproject_buildrequires

%prep
%autosetup -n scantpaper-%{version}

%build
%pyproject_wheel

# Generate gettext message catalogs.
python3 dev/compile_mo.py \
    --src po \
    --out locale \
    --domain scantpaper

# Generate HTML documentation.
pandoc README.md -o documentation.html

%install
%pyproject_install

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
    %{buildroot}%{_metainfodir}/org.scantpaper.desktop.metainfo.xml

# Icons.
mkdir -p %{buildroot}%{_datadir}/icons
cp -a src/scantpaper/icons/* %{buildroot}%{_datadir}/icons/

# Documentation.
install -Dpm 0644 \
    README.md \
    %{buildroot}%{_docdir}/%{name}/README.md

install -Dpm 0644 \
    documentation.html \
    %{buildroot}%{_docdir}/%{name}/documentation.html

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

# Let RPM's Python packaging machinery own the Python files.
%pyproject_save_files scantpaper

%check
# The upstream test suite needs a graphical environment, so don't run it
# here yet. The GitHub Actions workflow should run the tests separately
# under Xvfb.

%files -f %{pyproject_files}
%doc README.md documentation.html

%{_bindir}/scantpaper

%{_datadir}/applications/org.scantpaper.desktop
%{_metainfodir}/org.scantpaper.desktop.metainfo.xml

%{_datadir}/icons/hicolor/*/apps/*

%{_datadir}/locale/*/LC_MESSAGES/scantpaper.mo

%{_mandir}/man1/scantpaper.1*

%changelog
* Sun Sep 20 2026 Jeffrey Ratcliffe <jffry@posteo.net> - 3.0.19-1
- Initial RPM package
