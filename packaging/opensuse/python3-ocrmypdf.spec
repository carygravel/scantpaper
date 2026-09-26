Name:           python3-ocrmypdf
Version:        16.11.1
Release:        1%{?dist}
Summary:        OCR PDFs with tesseract

License:        MPL-2.0
URL:            https://github.com/ocrmypdf/OCRmyPDF
Source0:        https://files.pythonhosted.org/packages/source/o/ocrmypdf/ocrmypdf-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  python313-hatchling
BuildRequires:  python3-hatch-vcs
BuildRequires:  python3-setuptools-scm
BuildRequires:  python3dist(pikepdf) >= 8.10.1
BuildRequires:  python3dist(pillow) >= 10.0.1
BuildRequires:  python3dist(pluggy) >= 1
BuildRequires:  python3dist(rich) >= 13
BuildRequires:  python313-deprecation
BuildRequires:  python313-packaging

Requires:       ghostscript
Requires:       tesseract-ocr
Requires:       python313-deprecation
Requires:       python3-img2pdf >= 0.5
Requires:       python313-packaging
Requires:       python3-pdfminer.six >= 20220319
Requires:       python3dist(pikepdf) >= 8.10.1
Requires:       python3dist(pillow) >= 10.0.1
Requires:       python3dist(pluggy) >= 1
Requires:       python3dist(rich) >= 13

# The build and runtime dependencies are declared statically rather than
# generated, because ocrmypdf 16.11.1 lists "pi-heif" in its runtime
# requires while openSUSE Leap 16.0 only ships python313-pillow-heif
# (whose module is pillow_heif, not pi_heif); ocrmypdf imports pi_heif
# inside a try/except and degrades gracefully, so the unfulfillable
# requirement is intentionally not carried over.
#
# The version is derived from VCS tags by hatch-vcs; with pip's
# --no-build-isolation the version cannot be read from git, so it is pinned
# via the standard SETUPTOOLS_SCM_PRETEND_VERSION hook that setuptools-scm
# (used by hatch-vcs) honours.

%description
ocrMyPDF uses tesseract to add an OCR text layer to scanned PDF files,
making them searchable. It is rebuilt locally because openSUSE Leap 16.0
does not ship ocrmypdf built for python313, together with the source-built
toolchain packages (python3-img2pdf, python3-pdfminer.six, ...).

%prep
%autosetup -n ocrmypdf-%{version}

%build
SETUPTOOLS_SCM_PRETEND_VERSION=%{version} python3 -m pip wheel \
    --no-deps \
    --no-build-isolation \
    --wheel-dir dist/build \
    .

%install
python3 -m pip install \
    --root %{buildroot} \
    --prefix %{_prefix} \
    --no-deps \
    --no-index \
    --no-warn-script-location \
    dist/build/*.whl
find %{buildroot} \( -type f -o -type l \) \
    -printf '/%%P\n' \
    > %{_builddir}/%{name}-files.list

%check
PYTHONPATH=%{buildroot}%{python3_sitelib} \
    python3 -c 'import ocrmypdf; assert ocrmypdf.__version__ == "%{version}"'

%files -f %{_builddir}/%{name}-files.list
%license LICENSE
%doc README.md

%changelog
* Sat Sep 26 2026 ScantPaper maintainers <scantpaper@example.invalid> - 16.11.1-1
- Initial package (newest ocrmypdf whose dependencies exist on Leap 16.0;
  pi-heif runtime requirement intentionally dropped)