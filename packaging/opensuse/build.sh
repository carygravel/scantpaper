#!/usr/bin/env bash
#
# Build the openSUSE Leap 16 RPMs for ScantPaper and its locally packaged
# Python dependencies.
#
# This is the single source of truth for the openSUSE build. The CI workflow
# (.github/workflows/opensuse.yml) calls the same script so that a local build
# and a CI build behave identically. See README.md in this directory for
# usage and the openSUSE-specific gotchas that are encoded here.
#
# Subcommands:
#   setup              Install the build toolchain and configure rpmbuild.
#   build <pkg>        Fetch the source and run rpmbuild -ba for one package.
#   install <pkg>      Install the built RPMs for one package with zypper.
#   all                setup + build + install every package, in order.
#   collect <dir>      Copy every built RPM into <dir>.
#   collect-runtime <dir>
#                      Copy only the runtime RPMs (no build-only helpers, no
#                      -debuginfo / -debugsource) into <dir>.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPEC_DIR="$SCRIPT_DIR"

ORDER=(cysignals setuptools-scm hatch-vcs tesserocr iso639 sane pdfminer \
       img2pdf ocrmypdf scantpaper)

# The packages ScantPaper needs at run time, in build order. The build-only
# helper packages (python313-setuptools-scm, python313-hatch-vcs) are
# deliberately excluded: installing them on a target system drags in their own
# Python dependencies from the Leap backports repositories and buys nothing at
# run time. collect-runtime copies exactly this set (minus the -debuginfo /
# -debugsource packages) for publishing.
RUNTIME=(cysignals tesserocr iso639 sane pdfminer img2pdf ocrmypdf scantpaper)

# Package key -> spec file name.
spec_for() {
  case "$1" in
    cysignals)      echo python313-cysignals.spec ;;
    setuptools-scm) echo python313-setuptools-scm.spec ;;
    hatch-vcs)      echo python313-hatch-vcs.spec ;;
    tesserocr)      echo python313-tesserocr.spec ;;
    iso639)         echo python313-python-iso639.spec ;;
    sane)           echo python313-sane.spec ;;
    pdfminer)       echo python313-pdfminer.six.spec ;;
    img2pdf)        echo python313-img2pdf.spec ;;
    ocrmypdf)       echo python313-ocrmypdf.spec ;;
    scantpaper)     echo scantpaper.spec ;;
    *) echo "unknown package: $1" >&2; return 1 ;;
  esac
}

# Package key -> RPM name prefix used for the install glob.
rpmname_for() {
  case "$1" in
    cysignals)      echo python313-cysignals ;;
    setuptools-scm) echo python313-setuptools-scm ;;
    hatch-vcs)      echo python313-hatch-vcs ;;
    tesserocr)      echo python313-tesserocr ;;
    iso639)         echo python313-python-iso639 ;;
    sane)           echo python313-sane ;;
    pdfminer)       echo python313-pdfminer.six ;;
    img2pdf)        echo python313-img2pdf ;;
    ocrmypdf)       echo python313-ocrmypdf ;;
    scantpaper)     echo scantpaper ;;
    *) echo "unknown package: $1" >&2; return 1 ;;
  esac
}

# Package key -> patch file to copy into SOURCES (empty if none).
patch_for() {
  case "$1" in
    sane) echo python3-sane-snap-params-cache.patch ;;
    *) echo "" ;;
  esac
}

# Base toolchain. This mirrors what CI installs; the individual python
# build dependencies are all covered here so a local build is self-contained.
do_setup() {
  # openSUSE:repo-non-oss is preconfigured but disabled in the Leap 16 image.
  zypper -n --gpg-auto-import-keys modifyrepo -e openSUSE:repo-non-oss
  zypper -n --gpg-auto-import-keys ref
  zypper -n --gpg-auto-import-keys install --no-recommends \
    git curl tar gzip \
    rpm-build gcc gcc-c++ make pkgconf-pkg-config \
    python-rpm-macros python3-base python313-devel \
    python313-setuptools python313-pip python313-wheel \
    python313-Cython python313-build python313-flit-core \
    python313-hatchling python313-packaging python313-pytest \
    python313-polib python313-deprecation python313-tqdm \
    python313-rich python313-pluggy python313-cryptography \
    python313-charset-normalizer python313-Pillow python313-pikepdf \
    python313-numpy python313-pycairo python313-gobject \
    gtk3-devel typelib-1_0-Gtk-3_0 gobject-introspection-devel \
    tesseract-ocr-devel tesseract-ocr leptonica-devel \
    libcurl-devel libarchive-devel sane-backends-devel sane-backends \
    ghostscript poppler-tools tiff rsvg-convert ImageMagick \
    qpdf unpaper djvulibre xdg-utils gettext-tools help2man

  # Leap 16 has no distribution-release package, so %{dist} is empty. Define
  # the release suffix so built RPMs are versioned .lp160.1 like the distro.
  printf '%s\n' '%dist .lp160.1' > /usr/lib/rpm/macros.d/macros.dist

  # openSUSE's default rpm _topdir is /usr/src/packages; use ~/rpmbuild like
  # the Fedora packaging expects.
  mkdir -p "$HOME"/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
  printf '%%_topdir %s\n' "$HOME/rpmbuild" > "$HOME/.rpmmacros"
}

# Fetch the sdist declared by Source0 in a spec. Leap has no spectool or
# rpmdevtools (those are Fedora tools), so the URL is expanded with
# rpmspec -P and read back.
fetch_source() {
  local spec="$1"
  local url
  url=$(rpmspec -P "$HOME/rpmbuild/SPECS/$spec" |
    sed -n 's/^Source0:[[:space:]]*//p')
  curl -fL -o "$HOME/rpmbuild/SOURCES/$(basename "$url")" "$url"
}

do_build() {
  local pkg="$1"
  local spec rpmname patch
  spec="$(spec_for "$pkg")"
  rpmname="$(rpmname_for "$pkg")"
  patch="$(patch_for "$pkg")"

  cp "$SPEC_DIR/$spec" "$HOME/rpmbuild/SPECS/"
  if [ -n "$patch" ]; then
    cp "$SPEC_DIR/$patch" "$HOME/rpmbuild/SOURCES/"
  fi
  fetch_source "$spec"
  rpmbuild -ba "$HOME/rpmbuild/SPECS/$spec"
}

do_install() {
  local pkg="$1"
  local rpmname
  rpmname="$(rpmname_for "$pkg")"
  # shellcheck disable=SC2086  # glob must expand
  zypper -n install --allow-unsigned-rpm \
    "$HOME"/rpmbuild/RPMS/*/"$rpmname"-*.rpm
}

do_all() {
  do_setup
  local pkg
  for pkg in "${ORDER[@]}"; do
    do_build "$pkg"
    do_install "$pkg"
  done
}

do_collect() {
  local dir="$1"
  mkdir -p "$dir"
  find "$HOME/rpmbuild/RPMS" -type f -name '*.rpm' -exec cp {} "$dir"/ \;
  echo "Copied $(find "$dir" -maxdepth 1 -name '*.rpm' | wc -l) RPMs to $dir"
}

do_collect_runtime() {
  local dir="$1"
  mkdir -p "$dir"
  local pkg rpmname file
  for pkg in "${RUNTIME[@]}"; do
    rpmname="$(rpmname_for "$pkg")"
    while IFS= read -r file; do
      cp "$file" "$dir"/
    done < <(find "$HOME/rpmbuild/RPMS" -type f \
        -name "$rpmname-*.rpm" \
        ! -name '*-debuginfo-*' \
        ! -name '*-debugsource-*')
  done
  echo "Copied $(find "$dir" -maxdepth 1 -name '*.rpm' | wc -l) RPMs to $dir"
}

case "${1:-}" in
  setup)  do_setup ;;
  build)  do_build "${2:?usage: build <pkg>}" ;;
  install) do_install "${2:?usage: install <pkg>}" ;;
  all)    do_all ;;
  collect) do_collect "${2:?usage: collect <dir>}" ;;
  collect-runtime) do_collect_runtime "${2:?usage: collect-runtime <dir>}" ;;
  *) echo "usage: $0 {setup|build <pkg>|install <pkg>|all|collect <dir>|collect-runtime <dir>}" >&2
     exit 1 ;;
esac
