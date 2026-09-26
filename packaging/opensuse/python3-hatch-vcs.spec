Name:           python3-hatch-vcs
Version:        0.5.0
Release:        1%{?dist}
Summary:        Hatch plugin for versioning from VCS tags

License:        MIT
URL:            https://github.com/ofek/hatch-vcs
Source0:        https://files.pythonhosted.org/packages/source/h/hatch-vcs/hatch_vcs-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  python313-hatchling
BuildRequires:  python313-packaging

Requires:       python313-hatchling
Requires:       python313-packaging
Requires:       python313-setuptools
Requires:       python3-setuptools-scm

%description
hatch-vcs is a Hatchling plugin for versioning packages from VCS tags. It
is rebuilt locally because openSUSE Leap 16.0 does not ship python313
hatch-vcs, and ocrmypdf uses it as a build backend.

# The build uses hatchling (via pip --no-build-isolation); the self-named
# entry in its [build-system].requires is not enforced when isolation is
# off, and the wheel is versioned from the sdist's PKG-INFO.

%prep
%autosetup -n hatch_vcs-%{version}

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
    python3 -c 'import importlib.metadata as m; print(m.version("hatch_vcs"))'

%files -f %{_builddir}/%{name}-files.list
%license LICENSE.txt
%doc README.md

%changelog
* Sat Sep 26 2026 ScantPaper maintainers <scantpaper@example.invalid> - 0.5.0-1
- Initial package (build backend for the locally built ocrmypdf)