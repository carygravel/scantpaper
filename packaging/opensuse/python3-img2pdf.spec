Name:           python3-img2pdf
Version:        0.6.3
Release:        1%{?dist}
Summary:        Lossless conversion of raster images to PDF

License:        LGPL-3.0-or-later
URL:            https://github.com/josch/img2pdf
Source0:        https://files.pythonhosted.org/packages/source/i/img2pdf/img2pdf-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python-rpm-macros
BuildRequires:  python3-base
BuildRequires:  python313-devel
BuildRequires:  python313-pip
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
BuildRequires:  python313-build
BuildRequires:  python313-flit-core
BuildRequires:  python3dist(pillow)
BuildRequires:  python313-pikepdf

Requires:       python3dist(pillow)
Requires:       python313-pikepdf

%description
img2pdf converts raster images to PDF without loss of quality. It is
rebuilt locally because openSUSE Leap 16.0 does not ship python313-img2pdf.

%prep
%autosetup -n img2pdf-%{version}

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
    python3 -c 'import img2pdf; print(img2pdf.default_dpi)'

%files -f %{_builddir}/%{name}-files.list
%doc README.md
%license LICENSE

%changelog
* Sat Sep 26 2026 ScantPaper maintainers <scantpaper@example.invalid> - 0.6.3-1
- Initial package (PDF conversion tool for scantpaper and ocrmypdf)