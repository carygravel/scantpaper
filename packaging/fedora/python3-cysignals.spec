Name:           python3-cysignals
Version:        1.11.4
Release:        1%{?dist}
Summary:        Interrupt and signal handling for Cython

License:        LGPL-3.0-or-later
URL:            https://github.com/sagemath/cysignals
Source0:        https://files.pythonhosted.org/packages/source/c/cysignals/cysignals-%{version}.tar.gz

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros
BuildRequires:  python3-Cython
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make

%description
cysignals provides mechanisms for handling interrupts, signals,
and errors in Cython code.

It is used by Cython extensions that need reliable handling of
signals such as SIGINT while executing native code.

%generate_buildrequires
%pyproject_buildrequires -r

%prep
%autosetup -n cysignals-%{version}

%build
%pyproject_wheel

%install
%pyproject_install

%pyproject_save_files cysignals

%check
PYTHONPATH=%{buildroot}%{python3_sitearch} \
    python3 -c 'import cysignals; from cysignals import signals'

%files -f %{pyproject_files}
%license LICENSE
%doc README.rst

%{_bindir}/cysignals-CSI
%{_datadir}/cysignals/

%changelog
* Sun Sep 20 2026 ScantPaper maintainers <scantpaper@example.invalid> - 1.11.4-1
- Initial package
