Name:           python3-iso639
Version:        2026.7.23
Release:        1%{?dist}
Summary:        ISO 639 language codes, names, and other associated information

License:        Apache-2.0
URL:            https://github.com/jacksonllee/iso639
Source0:        https://files.pythonhosted.org/packages/source/p/python-iso639/python_iso639-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  pyproject-rpm-macros

%description
python-iso639 provides ISO 639 language codes, names, and other associated
information. scantpaper requires the modern API (iso639.Language) which the
Fedora python3-iso639 package (based on the old 0.1.x library) does not
provide.

%generate_buildrequires
%pyproject_buildrequires

%prep
%autosetup -n python_iso639-%{version}

%build
%pyproject_wheel

%install
%pyproject_install

%pyproject_save_files iso639

%check
PYTHONPATH=%{buildroot}%{python3_sitelib} \
    python3 -c 'import iso639; assert iso639.Language.from_part2t("fra").name == "French"'

%files -f %{pyproject_files}
%license LICENSE.txt
%doc README.md

%changelog
* Tue Sep 22 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2026.7.23-1
- Initial package