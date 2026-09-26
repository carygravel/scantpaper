Name:           python3-tesserocr
Version:        2.11.0
Release:        1%{?dist}
Summary:        Python wrapper for the Tesseract OCR API

License:        MIT
URL:            https://github.com/sirfz/tesserocr
Source0:        https://github.com/sirfz/tesserocr/archive/refs/tags/v%{version}.tar.gz

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  python313-Cython
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  pkgconf-pkg-config
BuildRequires:  tesseract-ocr-devel
BuildRequires:  tesseract-ocr
BuildRequires:  leptonica-devel
# tesserocr's build links -lcurl and -larchive directly.
BuildRequires:  libcurl-devel
BuildRequires:  libarchive-devel
BuildRequires:  python3-cysignals >= 1.11.4

Requires:       python3-cysignals >= 1.11.4
Requires:       tesseract-ocr

%description
tesserocr is a simple Python wrapper around the Tesseract OCR API.
It provides access to Tesseract's OCR engine from Python and releases
the Python GIL while processing images.

%prep
%autosetup -n tesserocr-%{version}

%build
# tesserocr's metadata/Cython step links against tesseract; Leap's Cython
# 3.0.12 satisfies the <3.2 constraint, so this does not need the static
# build-requires workaround the Fedora 44 spec uses.
python3 -m pip wheel \
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
# Run outside the source tree so the buildroot package shadows the source
# directories (which lack the compiled extension modules).
cd / && PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import tesserocr; print(tesserocr.PyTessBaseAPI.Version())'

%files -f %{_builddir}/%{name}-files.list
%doc README.rst
%license LICENSE

%changelog
* Sun Sep 20 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2.11.0-1
- Initial openSUSE package
- Build via pip wheel (no %pyproject_* macros on openSUSE); links -lcurl/-larchive