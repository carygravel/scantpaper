Name:           python3-sane
Version:        2.9.2
Release:        1%{?dist}
Summary:        Python interface to SANE scanners

License:        MIT
URL:            https://github.com/python-pillow/Sane
Source0:        https://files.pythonhosted.org/packages/source/p/python-sane/python_sane-%{version}.tar.gz
# Fix SaneDev.snap() failing with SANE_STATUS_INVAL against backends (e.g.
# Epson epsonscan2) that return INVAL on a second sane_get_parameters() call
# after sane_start. https://github.com/python-pillow/Sane/pull/109
Patch0:         python3-sane-snap-params-cache.patch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  gcc
BuildRequires:  make
BuildRequires:  sane-backends-devel
BuildRequires:  sane-backends

Requires:       libsane1
Requires:       python3dist(numpy)
Requires:       python3dist(pillow)

%description
python-sane is a Python interface to the SANE scanner API. It is built from
source with a local patch (PR 109) so that its python3dist(python-sane)
provide matches what scantpaper expects, and to fix scan failures against
backends such as Epson epsonscan2.

%prep
%autosetup -n python_sane-%{version}

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
* Tue Sep 22 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2.9.2-1
- Initial openSUSE package with snap() cached-parameters fix (PR 109)