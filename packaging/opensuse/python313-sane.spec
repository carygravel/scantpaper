%{!?pyflavor:%define pyflavor 313}
Name:           python%{pyflavor}-sane
# A repository also offers this package at the same upstream version, so the
# RPM version carries a trailing ".0". That keeps our build ahead of theirs
# without an epoch (which openSUSE's packaging guidelines discourage), while
# still yielding to any future upstream release. pkg_version below is the
# real upstream version, used for the tarball name and the unpack directory.
%define pkg_version 2.9.2
Version:        %{pkg_version}.0
Release:        1%{?dist}
Summary:        Python interface to SANE scanners

License:        MIT
URL:            https://github.com/python-pillow/Sane
Source0:        https://files.pythonhosted.org/packages/source/p/python-sane/python_sane-%{pkg_version}.tar.gz
# Fix SaneDev.snap() failing with SANE_STATUS_INVAL against backends (e.g.
# Epson epsonscan2) that return INVAL on a second sane_get_parameters() call
# after sane_start. https://github.com/python-pillow/Sane/pull/109
Patch0:         python3-sane-snap-params-cache.patch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python%{pyflavor}-devel
BuildRequires:  python%{pyflavor}-pip
BuildRequires:  python%{pyflavor}-setuptools
BuildRequires:  python%{pyflavor}-wheel
BuildRequires:  python%{pyflavor}-build
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  sane-backends-devel
BuildRequires:  sane-backends

Requires:       libsane1
Requires:       python%{pyflavor}-numpy
Requires:       python%{pyflavor}-Pillow

%if 0%{?suse_version} >= 1699
# Tumbleweed's python-sane provides these unversioned names; keep them when
# this patched build replaces the distribution package.
Provides:       python3-sane = %{version}
Provides:       python3dist(python-sane) = %{version}
%endif

%description
python-sane is a Python interface to the SANE scanner API. It is built from
source with a local patch (PR 109) that fixes SaneDev.snap() failing with
SANE_STATUS_INVAL against backends, such as Epson's epsonscan2, that return
INVAL on a second sane_get_parameters() call after sane_start.

%prep
%autosetup -n python_sane-%{pkg_version}

%build
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
    python3 -c 'import sane; print(sane.__version__)'

%files -f %{_builddir}/%{name}-files.list
%doc README.rst
%license COPYING

%changelog
* Tue Sep 22 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2.9.2.0-1
- Initial openSUSE package with snap() cached-parameters fix (PR 109)