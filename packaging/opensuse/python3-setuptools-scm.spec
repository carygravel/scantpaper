Name:           python3-setuptools-scm
Version:        8.2.1
Release:        1%{?dist}
Summary:        The blessed package to manage your versions by scm tags

License:        MIT
URL:            https://github.com/pypa/setuptools-scm
Source0:        https://files.pythonhosted.org/packages/source/s/setuptools-scm/setuptools_scm-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build

Requires:       python3dist(packaging)
Requires:       python3dist(setuptools)

%description
setuptools-scm helps manage package versions by SCM tags. It is rebuilt
locally because openSUSE Leap 16.0 does not ship python313-setuptools-scm,
yet the pdfminer.six and hatch-vcs packages (of the ocrmypdf toolchain)
need it as a build backend.

%prep
%autosetup -n setuptools_scm-%{version}

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
PYTHONPATH=%{buildroot}%{python3_sitelib} \
    python3 -c 'import setuptools_scm; print(setuptools_scm.get_version())' \
    || true

%files -f %{_builddir}/%{name}-files.list
%license LICENSE
%doc README.md

%changelog
* Sat Sep 26 2026 ScantPaper maintainers <scantpaper@example.invalid> - 8.2.1-1
- Initial package (build backend for the locally built PDF toolchain)