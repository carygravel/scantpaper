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

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros
BuildRequires:  gcc
BuildRequires:  sane-backends-devel

Requires:       libsane.so.1
Requires:       python3-numpy
Requires:       python3-pillow

%description
python-sane is a Python interface to the SANE scanner API. It is built from
source with a local patch (PR 109) so that its python3dist(python-sane)
provide matches what scantpaper expects, and to fix scan failures against
backends such as Epson epsonscan2.

%generate_buildrequires
%pyproject_buildrequires

%prep
%autosetup -n python_sane-%{version}

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files sane _sane

%check
PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import sane; print(sane.__version__)'

%files -f %{pyproject_files}
%doc README.rst
%license COPYING

%changelog
* Tue Sep 22 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2.9.2-1
- Initial package with snap() cached-parameters fix (PR 109)