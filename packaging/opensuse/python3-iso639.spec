Name:           python3-iso639
Version:        2026.7.23
Release:        1%{?dist}
Summary:        ISO 639 language codes, names, and other associated information

License:        Apache-2.0
URL:            https://github.com/jacksonllee/iso639
Source0:        https://files.pythonhosted.org/packages/source/p/python-iso639/python_iso639-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build

%description
python-iso639 provides ISO 639 language codes, names, and other associated
information. scantpaper requires the modern API (iso639.Language) which the
openSUSE python3-iso639 package (based on the old 0.1.x library) does not
provide, so the current version is built from source.

%prep
%autosetup -n python_iso639-%{version}

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
    python3 -c \
    'import iso639; assert iso639.Language.from_part2t("fra").name == "French"'

%files -f %{_builddir}/%{name}-files.list
%license LICENSE.txt
%doc README.md

%changelog
* Tue Sep 22 2026 ScantPaper maintainers <scantpaper@example.invalid> - 2026.7.23-1
- Initial openSUSE package