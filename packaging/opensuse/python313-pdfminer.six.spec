Name:           python313-pdfminer.six
# A repository also offers this package at the same upstream version, so the
# RPM version carries a trailing ".0". That keeps our build ahead of theirs
# without an epoch (which openSUSE's packaging guidelines discourage), while
# still yielding to any future upstream release. pkg_version below is the
# real upstream version, used for the tarball name and the unpack directory.
%define pkg_version 20260107
Version:        %{pkg_version}.0
Release:        1%{?dist}
Summary:        PDF parser and analyzer

License:        MIT
URL:            https://github.com/py-pdf/pdfminer.six
Source0:        https://files.pythonhosted.org/packages/source/p/pdfminer.six/pdfminer_six-%{pkg_version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  python313-setuptools-scm
BuildRequires:  python313-cryptography
BuildRequires:  python313-charset-normalizer

Requires:       python313-charset-normalizer
Requires:       python313-cryptography

%description
pdfminer.six is a tool and library for extracting information from PDF
documents. It is rebuilt locally because openSUSE Leap 16.0 ships neither
the python313-pdfminer.six package nor the ocrmypdf that would use it.

%prep
%autosetup -n pdfminer_six-%{pkg_version}

%build
# setuptools-scm derives the version from VCS tags; with pip's
# --no-build-isolation the version cannot be read from git, so pin it via
# the standard SETUPTOOLS_SCM_PRETEND_VERSION hook. The wheel carries the real
# upstream version, not the RPM's ".0" packaging suffix, so the installed
# metadata matches what PyPI publishes.
SETUPTOOLS_SCM_PRETEND_VERSION=%{pkg_version} python3 -m pip wheel \
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
    python3 -c 'from pdfminer.high_level import extract_text; print("ok")'

%files -f %{_builddir}/%{name}-files.list
%doc README.md
%license LICENSE

%changelog
* Sat Sep 26 2026 ScantPaper maintainers <scantpaper@example.invalid> - 20260107.0-1
- Initial package (PDF text extraction backend for the ocrmypdf toolchain)