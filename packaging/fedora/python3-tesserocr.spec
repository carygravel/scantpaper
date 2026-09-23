Name:           python3-tesserocr
Version:        2.11.0
Release:        1%{?dist}
Summary:        Python wrapper for the Tesseract OCR API

License:        MIT
URL:            https://github.com/sirfz/tesserocr
Source0:        https://github.com/sirfz/tesserocr/archive/refs/tags/v%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-Cython
BuildRequires:  gcc-c++
BuildRequires:  pkgconf-pkg-config
BuildRequires:  tesseract-devel
BuildRequires:  leptonica-devel

BuildRequires:  python3-cysignals >= 1.11.4

Requires:       python3-cysignals >= 1.11.4
Requires:       tesseract
Requires:       leptonica

%description
tesserocr is a simple Python wrapper around the Tesseract OCR API.
It provides access to Tesseract's OCR engine from Python and releases
the Python GIL while processing images.

# The build and runtime dependencies are declared statically below rather
# than generated with %pyproject_buildrequires, because tesserocr's build
# backend requires Cython >= 3.0,<3.2 while Fedora 44 ships Cython 3.2.x;
# on Fedora 44 rpmbuild enforces the generated requirement and the build
# would fail. Cython 3.2 compiles tesserocr fine, so the constraint is
# intentionally not carried over.

%prep
%autosetup -n tesserocr-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files tesserocr

%check
echo "=== source tree ==="
find . -maxdepth 2 -type f | sort | grep -E 'tesserocr|\.so$' || true

echo "=== buildroot ==="
find %{buildroot} -type f | sort | grep -E 'tesserocr|\.so$' || true

echo "=== Python paths ==="
cd /
PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import sys; print("\n".join(sys.path))'

echo "=== import ==="
PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import tesserocr; print(tesserocr.__file__); print(tesserocr.PyTessBaseAPI.Version())'

%files -f %{pyproject_files}
%doc README.rst
%license LICENSE

%changelog
* Sun Sep 20 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2.11.0-1
- Initial package
