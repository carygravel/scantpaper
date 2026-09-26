Name:           python3-cysignals
Version:        1.11.4
Release:        1%{?dist}
Summary:        Interrupt and signal handling for Cython

License:        LGPL-3.0-or-later
URL:            https://github.com/sagemath/cysignals
Source0:        https://files.pythonhosted.org/packages/source/c/cysignals/cysignals-%{version}.tar.gz

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

%description
cysignals provides mechanisms for handling interrupts, signals,
and errors in Cython code.

It is used by Cython extensions that need reliable handling of
signals such as SIGINT while executing native code.

%prep
%autosetup -n cysignals-%{version}

%build
# openSUSE's python-rpm-macros provide no pipelined pyproject macros, and
# the setup.py-based python_build macro cannot build PEP 517 backends, so
# build the wheel directly with pip (the build-system requires are not
# enforced because --no-build-isolation is used; every backend dependency
# is installed explicitly above).
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
# Generate the file list from the installed tree (as the Fedora
# pyproject_save_files macro would; it does not exist on openSUSE).
find %{buildroot} \( -type f -o -type l \) \
    -printf '/%%P\n' \
    > %{_builddir}/%{name}-files.list

%check
PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import cysignals; from cysignals import signals'

%files -f %{_builddir}/%{name}-files.list
%license LICENSE
%doc README.rst

%changelog
* Sun Sep 20 2026 ScantPaper maintainers <scantpaper@example.invalid> - 1.11.4-1
- Initial openSUSE package
- Build via pip wheel (no %pyproject_* macros on openSUSE)