#!/usr/bin/env bash
# Build and optionally upload the jammy PPA source packages for the
# ocrmypdf 16.13.0 dependency stack (ppa:jeffreyratcliffe/gscan2pdf-ppa).
#
# Sources come from the Debian and Ubuntu archives.  Each package is
# unpacked with dpkg-source, adjusted for jammy (build deps that jammy
# does not have are dropped, test suites are disabled, and documentation
# binary packages that would need sphinx packages absent from jammy are
# removed), re-versioned as <upstream>-0~ppaNjammy and built with
# debuild -S -sa.  With --upload, each result is pushed to the PPA with
# dput, in dependency order.
#
# Usage:
#   build_ppa_stack.sh [--dry-run] [--upload] [--only NAME] [--from NAME]
#                      [--pparev N] [--keep]
#
# Environment:
#   WORK=/tmp/ppa-jammy            working directory (kept with --keep)
#   BUILDER="debuild -S -sa -d"    source-only build (skip local build-dep check)
#   PPA=gscan2pdf-ppa              dput destination
#   MIRROR_DEBIAN / MIRROR_UBUNTU  override the pool mirrors
#
# Bumping versions / adding packages:
#   edit the version field in PACKAGES (or add a new line) and, if the
#   package needs jammy adjustments, a customize_<name>() function.
set -euo pipefail

MIRROR_DEBIAN="${MIRROR_DEBIAN:-http://deb.debian.org/debian}"
MIRROR_UBUNTU="${MIRROR_UBUNTU:-http://archive.ubuntu.com/ubuntu}"
PPA="${PPA:-gscan2pdf-ppa}"
RELEASE="${RELEASE:-jammy}"
# ocrmypdf 17.10 requires Python >=3.11, so it cannot be built for jammy.
# Jammy and the noble PPA stack stay on 16.13; resolute and stonking use
# 17.10, whose runtime dependencies are already in those archives.
case "$RELEASE" in
    resolute|stonking) OCRMYPDF_VERSION="17.10.0+dfsg1-1" ;;
    *) OCRMYPDF_VERSION="16.13.0+dfsg1-2" ;;
esac
# Directory holding this script; the pillow-sane customize hook reads the
# vendored epsonscan2 patch from here, next to the other package sources.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PPAREV=1
WORK="${WORK:-/var/tmp/ppa-jammy}"
BUILDER="${BUILDER:-debuild -S -sa -d}"
DRY_RUN=0
DO_UPLOAD=0
KEEP=0
ONLY=""
FROM=""
# The PPA still carries the broken 78.1.1 line, which sorts higher than
# 68.1.2; pin the consumers to the exact working version so the chroot
# never resolves to 78.1.1 again.
SETUPTOOLS_PIN="${SETUPTOOLS_PIN:-68.1.2-0~ppa1jammy}"

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=1 ;;
        --upload) DO_UPLOAD=1 ;;
        --only) ONLY="$2"; shift ;;
        --from) FROM="$2"; shift ;;
        --pparev) PPAREV="$2"; shift ;;
        --keep) KEEP=1 ;;
        -h|--help)
            sed -n '2,12p;15,22p' "$0"
            exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
    shift
done

mkdir -p "$WORK"

# ---------------------------------------------------------------------
# PACKAGES: name|pool-dir|version|mirror
#   pool-dir  path under /pool/<section>/..., e.g. main/p/python-packaging
#   mirror    "debian" (deb.debian.org) or "ubuntu" (archive.ubuntu.com)
# ---------------------------------------------------------------------
PACKAGES=(
    "python-packaging|main/p/python-packaging|26.2-2|debian"
    "setuptools|main/s/setuptools|68.1.2-2|debian"
    "wheel|main/w/wheel|0.47.0-1|debian"
    "python-pathspec|main/p/python-pathspec|0.12.1-1|debian"
    "python-editables|main/p/python-editables|0.5-3|debian"
    "trove-classifiers|main/t/trove-classifiers|2026.1.14.14-1|debian"
    "python-exceptiongroup|main/p/python-exceptiongroup|1.2.2-1|debian"
    "python-iso639|main/p/python-iso639|2025.2.18-1|debian"
    "pyproject-metadata|main/p/pyproject-metadata|0.11.0-1|debian"
    "hatchling|main/h/hatchling|1.27.0-1|debian"
    "hatch-vcs|main/h/hatch-vcs|0.4.0-1|debian"
    "scikit-build-core|main/s/scikit-build-core|0.11.6-2|debian"
    "qpdf|main/q/qpdf|12.3.2-1|debian"
    "pybind11|main/p/pybind11|3.0.1-3|debian"
    "pikepdf|main/p/pikepdf|10.5.0+dfsg-2|debian"
    "pillow|main/p/pillow|10.2.0-1build1|ubuntu"
    "pillow-sane|universe/p/pillow-sane|2.9.2-1build2|ubuntu"
    "img2pdf|main/i/img2pdf|0.6.2-1|debian"
    "pdfminer|main/p/pdfminer|20260107+dfsg-1|debian"
    "mdurl|main/m/mdurl|0.1.2-1|debian"
    "uc-micro-py|main/u/uc-micro-py|1.0.3-1|debian"
    "linkify-it-py|main/l/linkify-it-py|2.0.3-1|debian"
    "markdown-it-py|main/m/markdown-it-py|3.0.0-3|debian"
    "pygments|main/p/pygments|2.20.0+dfsg-2|debian"
    "python-typing-extensions|main/p/python-typing-extensions|4.10.0-1|ubuntu"
    "rich|main/r/rich|13.9.4-1|debian"
    "ocrmypdf|main/o/ocrmypdf|$OCRMYPDF_VERSION|debian"
)

# OCRmyPDF 17.10's fpdf2 renderer calls TTFFont.escape_text, which first
# appears in fpdf2 2.8.9. Resolute and stonking carry 2.8.4/2.8.8, so build
# the newer fpdf2 for those series. The 16.13 stack does not use fpdf2.
if [[ "$RELEASE" == resolute || "$RELEASE" == stonking ]]; then
    PACKAGES=("fpdf2|main/f/fpdf2|2.8.9-1|debian" "${PACKAGES[@]}")
fi

# ---------------------------------------------------------------------
# debian/control editor.  Operations:
#   strip             remove entries tagged <!nocheck> / <!nodoc>
#   dropdeps TK...    remove Build-Depends(-Indep) entries with those tokens
#   dropbin PKG...    remove binary package stanzas + references to them
#   dropfield FIELD   remove a whole Source-level field
#   replacedep TK NEW replace (or append) a Depends entry in binary stanzas
#   addbd ENTRY...     append entries to the source Build-Depends field
# ---------------------------------------------------------------------
cat > "$WORK/.edit_control.py" <<'PYEOF'
import re, sys

fn, op = sys.argv[1], sys.argv[2]
args = sys.argv[3:]

with open(fn, encoding='utf-8') as f:
    text = f.read()

paras = text.split('\n\n')

def parse_fields(para):
    fields = []
    cur = None
    for line in para.split('\n'):
        m = re.match(r'^([A-Za-z0-9][A-Za-z0-9-]*):(.*)$', line)
        if m:
            cur = [m.group(1), m.group(2).lstrip(' ')]
            fields.append(cur)
        elif cur is not None and line[:1] in (' ', '\t'):
            cur[1] += '\n' + line.rstrip()
    return fields

def build_fields(fields):
    out = []
    for name, value in fields:
        if value.startswith('\n'):
            out.append(name + ':' + value)
        else:
            out.append(name + ': ' + value)
    return '\n'.join(out)

def entries(value):
    joined = ' '.join(l.strip() for l in value.split('\n') if l.strip())
    return [e.strip() for e in joined.split(',') if e.strip()]

def format_entries(es):
    if not es:
        return ''
    return '\n' + '\n'.join(' ' + e + ',' for e in es)

def token(e):
    return e.split()[0].split('(')[0].split('<')[0].strip()

def apply_bd(fields, fn_):
    changed = False
    for f in fields:
        if f[0] in ('Build-Depends', 'Build-Depends-Indep'):
            new = fn_(entries(f[1]))
            if new != entries(f[1]):
                f[1] = format_entries(new)
                changed = True
    return changed

if op == 'strip':
    def strip(es):
        return [e for e in es if '<!nocheck>' not in e and '<!nodoc>' not in e]
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        if apply_bd(fields, strip):
            paras[i] = build_fields(fields)

elif op == 'dropdeps':
    drop = set(args)
    def drop_fn(es):
        return [e for e in es if token(e) not in drop]
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        changed = apply_bd(fields, drop_fn)
        for f in fields:
            if f[0] in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests',
                        'Provides', 'Conflicts', 'Breaks', 'Replaces'):
                es = entries(f[1])
                new = drop_fn(es)
                if new != es:
                    f[1] = format_entries(new)
                    changed = True
        if changed:
            paras[i] = build_fields(fields)

elif op == 'dropfield':
    target = args[0]
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        fields = [f for f in fields if f[0] != target]
        paras[i] = build_fields(fields)

elif op == 'dropbin':
    drop = set(args)
    new_paras = []
    for para in paras:
        fields = parse_fields(para)
        pkg = None
        for name, value in fields:
            if name == 'Package':
                pkg = value.strip()
        if pkg in drop:
            continue
        for f in fields:
            if f[0] in ('Depends', 'Pre-Depends', 'Recommends', 'Suggests',
                        'Provides', 'Conflicts', 'Breaks', 'Replaces'):
                es = entries(f[1])
                new = [e for e in es if token(e) not in drop]
                if new != es:
                    f[1] = format_entries(new)
        new_paras.append(build_fields(fields))
    paras = new_paras

elif op == 'replacedep':
    t, newentry = args[0], args[1]
    found = False
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        for f in fields:
            if f[0] == 'Depends':
                es = entries(f[1])
                if any(token(e) == t for e in es):
                    f[1] = format_entries([newentry if token(e) == t else e for e in es])
                    found = True
        if found:
            paras[i] = build_fields(fields)
            break
    if not found:
        for i, para in enumerate(paras):
            fields = parse_fields(para)
            if any(n == 'Package' for n, _ in fields):
                for f in fields:
                    if f[0] == 'Depends':
                        f[1] = format_entries(entries(f[1]) + [newentry])
                        paras[i] = build_fields(fields)
                        found = True
                        break
            if found:
                break

elif op == 'addbd':
    target = args
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        if any(n == 'Package' for n, _ in fields):
            continue
        for f in fields:
            if f[0] == 'Build-Depends':
                es = entries(f[1])
                existing = {token(e) for e in es}
                es = es + [a for a in target if token(a) not in existing]
                f[1] = format_entries(es)
                paras[i] = build_fields(fields)
                break
        else:
            continue
        break

elif op == 'replacebd':
    t, newentry = args[0], args[1]
    for i, para in enumerate(paras):
        fields = parse_fields(para)
        if any(n == 'Package' for n, _ in fields):
            continue
        for f in fields:
            if f[0] in ('Build-Depends', 'Build-Depends-Indep'):
                es = entries(f[1])
                if any(token(e) == t for e in es):
                    f[1] = format_entries([newentry if token(e) == t else e for e in es])
                    paras[i] = build_fields(fields)
                break
        else:
            continue
        break

with open(fn, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(paras))
PYEOF

ec() { python3 "$WORK/.edit_control.py" "$@"; }

# Skip the test suite of a package: pybuild's dh_auto_test honours
# DEB_BUILD_OPTIONS=nocheck.  Added to every rules file.
disable_tests() {
    sed -i '1a export DEB_BUILD_OPTIONS += nocheck' "$1/debian/rules"
}

# Convert a PEP 639 SPDX string license (flit_core >= 3.9) back to the
# PEP 621 dict form required by jammy's flit_core 3.6.0.
flit_license_dict() {
    sed -i -E 's/^license = ("[^"]+")/license = {text = \1}/' "$1/pyproject.toml"
}

# flit_core 3.6.0 rejects ** globs; drop only the [tool.flit.sdist] patterns.
flit_sdist_no_glob() {
    local f="$1/pyproject.toml"
    awk '
        /^\[tool\.flit\.sdist\]/ { in_sdist=1; print; next }
        /^\[/ { in_sdist=0 }
        in_sdist && /\*\*/ { next }
        { print }
    ' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
}

# ---------------------------------------------------------------------
# Per-package jammy adjustments.  The $1 arg is the extracted source dir.
# ---------------------------------------------------------------------
customize_python-packaging() {
    ec "$1/debian/control" strip
    flit_license_dict "$1"
}

customize_setuptools() {
    local c="$1/debian/control" r="$1/debian/rules"
    ec "$c" strip
    ec "$c" dropdeps python3-alabaster python3-sphinx python3-sphinx-favicon \
        python3-sphinx-reredirects python3-sphinx-notfound-page
    # doc html is never built (sphinx deps dropped); drop the doc package
    ec "$c" dropbin python-setuptools-doc
    # bookworm's Build-Conflicts would remove python3-setuptools from the
    # chroot, leaving pybuild nothing to build the wheel with
    ec "$c" dropfield Build-Conflicts
    sed -i 's/--with python3,sphinxdoc/--with python3/' "$r"
    sed -i '/MAKE.*-C docs html/d' "$r"
    sed -i '/dh_installdocs -p python-setuptools-doc docs\/build\/html/d' "$r"
    sed -i '/dh_link -p python-setuptools-doc/,+2d' "$r"
}

customize_wheel() {
    local c="$1/debian/control" r="$1/debian/rules"
    # bookworm's dh-python (>= 6) and test-only deps (tox (>= 4),
    # python3-setuptools (>= 77) <!nocheck>) are not satisfiable on jammy
    ec "$c" strip
    ec "$c" replacebd dh-python 'dh-python'
    # sphinx manpage build needs python3-sphinx (stripped); drop the hook and
    # the .manpages file that still points at the never-built man page
    sed -i '/^execute_before_dh_installman:/,+7d' "$r"
    rm -f "$1"/debian/*.manpages
    flit_license_dict "$1"
    flit_sdist_no_glob "$1"
}

customize_pyproject-metadata() {
    ec "$1/debian/control" strip
    flit_license_dict "$1"
    flit_sdist_no_glob "$1"
    # flit 3.6.0 lacks the hyphen->underscore module fallback
    sed -i '/^\[tool\.flit\.sdist\]/i [tool.flit.module]\nname = "pyproject_metadata"\n' "$1/pyproject.toml"
}

customize_python-exceptiongroup() {
    # jammy has no python3-flit-scm; build with plain flit_core + static version
    local py="$1/pyproject.toml" c="$1/debian/control"
    sed -i 's/build-backend = "flit_scm:buildapi"/build-backend = "flit_core.buildapi"/' "$py"
    sed -i 's/requires = \["flit_scm"\]/requires = ["flit_core >= 3.2"]/' "$py"
    sed -i 's/^dynamic = \["version"\]/version = "1.2.2"/' "$py"
    # upstream generates _version.py via flit_scm; static fallback for jammy
    sed -i 's/^from \._version import version as __version__.*/__version__ = "1.2.2"/' "$1/src/exceptiongroup/__init__.py"
    ec "$c" strip
    ec "$c" dropdeps python3-flit-scm
    ec "$c" addbd flit
}

customize_python-pathspec() {
    # flit_core resolves the version itself; flit-scm is not on jammy
    ec "$1/debian/control" dropdeps python3-flit-scm
}

customize_trove-classifiers() { ec "$1/debian/control" strip; }
customize_python-editables() { ec "$1/debian/control" strip; }
customize_python-iso639() {
    ec "$1/debian/control" strip
    # name/version come only from pyproject.toml [project], which needs
    # setuptools >= 61; pin the PPA's working 68.1.2 at build time
    ec "$1/debian/control" replacebd python3-setuptools "python3-setuptools (= $SETUPTOOLS_PIN)"
}
customize_hatch-vcs() { ec "$1/debian/control" strip; }

customize_scikit-build-core() {
    # jammy setuptools-scm (6.4.2) cannot read git-archive versions; use static
    local py="$1/pyproject.toml" v="${1##*-}"
    sed -i 's/^dynamic = \["version"\]/version = "'"$v"'"/' "$py"
    sed -i '/^version.source = "vcs"$/d; /^build.hooks.vcs.version-file = /d' "$py"
    # _version.py is gitignored and only produced by the vcs hook; set it statically
    sed -i 's/^from \._version import version as __version__/__version__ = "'"$v"'"/' "$1/src/scikit_build_core/__init__.py"
    ec "$1/debian/control" strip
}

customize_qpdf() {
    local c="$1/debian/control" r="$1/debian/rules"
    # jammy dpkg-dev is 1.21.1 (< 1.22.5); drop the floor
    ec "$c" dropdeps dpkg-dev
    # qpdf-doc needs sphinx-rtd-theme >= 1 (jammy: 0.5.1); drop docs
    ec "$c" dropfield Build-Depends-Indep
    ec "$c" dropbin qpdf-doc
    sed -i '/^execute_after_dh_auto_configure-indep:/,+3d' "$r"
}

customize_pybind11() {
    local c="$1/debian/control" r="$1/debian/rules"
    ec "$c" strip
    # myst-parser (docs only, untagged) drags in linkify-it-py >= 1.2.4,
    # which jammy lacks (1.2.2)
    ec "$c" dropdeps python3-myst-parser
    ec "$c" dropbin pybind11-doc
    # without sphinx the -doc package would fail; drop the sphinxdoc addon
    sed -i 's/--with sphinxdoc --buildsystem=cmake/--buildsystem=cmake/' "$r"
    # the rules' doc hooks (docs clean/html) only skip with nodoc, and
    # override_dh_installdocs copies into the dropped pybind11-doc package;
    # (nocheck is added later by disable_tests, so emit nodoc here)
    sed -i '1a export DEB_BUILD_OPTIONS += nodoc' "$r"
    sed -i '/^\tcp debian\/images\//d; /^\tsed "s|src=/d' "$r"
    # the bookworm scikit-build-core binary dropped exceptiongroup (its
    # python_version<'3.11' marker was evaluated on py3.11); the pybind11
    # wheel build needs it on jammy's python 3.10
    ec "$c" addbd python3-exceptiongroup
}

customize_pikepdf() {
    local c="$1/debian/control" r="$1/debian/rules" py="$1/pyproject.toml"
    ec "$c" dropdeps python3-ipython python3-lxml python3-matplotlib \
        python3-myst-parser python3-pil python3-sphinx python3-sphinx-autoapi \
        python3-sphinx-issues python3-sphinx-rtd-theme
    ec "$c" dropbin pikepdf-doc
    # 68.1.2's pyproject validator only accepts the PEP 621 dict license form
    sed -i 's/^license = "\(.*\)"$/license = {text = "\1"}/' "$py"
    # bookworm's setuptools >= 77.0.3 floor and scm-based versioning are not
    # usable on jammy; version is static in pyproject
    ec "$c" replacebd python3-setuptools "python3-setuptools (= $SETUPTOOLS_PIN)"
    ec "$c" dropdeps python3-setuptools-scm
    sed -i 's/--with sphinxdoc //' "$r"
    sed -i '/@set -ex; cd docs;/,/make html/d' "$r"
    sed -i '/^override_dh_sphinxdoc:/,+1d' "$r"
}

customize_img2pdf() {
    # the <nocheck> toolchain (libgs-common, mupdf-tools, ...) does not exist
    # on jammy; strip them.  flit_core 3.6.0 reads version from src/img2pdf.py.
    ec "$1/debian/control" strip
}

customize_pillow() {
    local c="$1/debian/control" r="$1/debian/rules"
    # python-pil-doc needs sphinx-inline-tabs (absent in jammy); drop docs
    ec "$c" dropfield Build-Depends-Indep
    ec "$c" dropbin python-pil-doc
    sed -i 's/^binary-indep: build build-doc-stamp install/binary-indep: build install/' "$r"
    sed -i 's/^build-indep: build build-doc-stamp/build-indep: build/' "$r"
    sed -i '/^build-doc-stamp:/,+2d' "$r"
    sed -i '/ppython-pil-doc/d' "$r"
    # setup.py carries no metadata; it all comes from pyproject [project],
    # which jammy's setuptools 59.6.0 cannot read (builds UNKNOWN-0.0.0 and
    # skips the pure-python modules). Pin the PPA's working 68.1.2.
    ec "$c" replacebd python3-setuptools "python3-setuptools (= $SETUPTOOLS_PIN)"
}

# python3-sane is the binary for the pillow-sane source package.  The newer
# series (questing/resolute/stonking) carry the same upstream 2.9.2 as the
# archive, so a bare -0~ppaN would tie upstream and lose the revision to the
# archive's -1buildN and never override it.  Keep the archive's full version
# and append a +ppa suffix instead - the same idiom Ubuntu uses for
# no-change rebuilds - so the PPA build outranks the archive on every series.
ppa_version_pillow-sane() {
    local dver="$1" rev
    rev=${dver#*-}
    echo "${dver%-*}-${rev}+ppa${PPAREV}${RELEASE}"
}

ppa_changelog_pillow-sane() {
    echo "Reuse cached SANE_Parameters in snap() instead of a second sane_get_parameters() call, fixing scans with Epson epsonscan2 backends (python-pillow/Sane PR #109)"
}

customize_pillow-sane() {
    # Apply the same epsonscan2 snap() params-cache patch that the Fedora and
    # openSUSE trees vendored (PR #109): drop it into debian/patches as a
    # Quilt patch and register it in the series.
    cp "$SCRIPT_DIR/python3-sane-snap-params-cache.patch" \
       "$1/debian/patches/python3-sane-snap-params-cache.patch"
    echo "python3-sane-snap-params-cache.patch" >> "$1/debian/patches/series"
}

customize_pdfminer() {
    local c="$1/debian/control" py="$1/pyproject.toml"
    # drop the unversioned python3-pytest (jammy 6.2.5 too old for the suite)
    ec "$c" dropdeps python3-pytest
    # jammy's python3-cryptography is 3.4.8; pdfminer only uses AES-CBC via
    # hazmat (all present in 3.4.8), so relax upstream's >= 36.0.0 floor
    sed -i 's/cryptography >= 36\.0\.0/cryptography >= 3.4.8/' "$py"
    # version is dynamic via setuptools-scm; jammy's 6.4.2 can't read the
    # git-archive version (no .git_archival.txt/PKG-INFO) and setuptools < 61
    # can't read [project] at all -- hardcode both
    sed -i 's/^dynamic = \["version"\]/version = "20260107"/' "$py"
    sed -i '/^\[tool\.setuptools_scm\]/{N;d}' "$py"
    # 68.1.2's pyproject validator only accepts the PEP 621 dict license form
    sed -i 's/^license = "\(.*\)"$/license = {text = "\1"}/' "$py"
    ec "$c" dropdeps python3-setuptools-scm
    ec "$c" replacebd python3-setuptools "python3-setuptools (= $SETUPTOOLS_PIN)"
}

customize_mdurl() { ec "$1/debian/control" strip; }

customize_linkify-it-py() {
    # python3-uc-micro is a build-dep only for the (skipped) test suite;
    # drop it so the build does not wait on the PPA uc-micro binary.  The
    # runtime dependency in the binary package is generated from pyproject.
    ec "$1/debian/control" dropdeps python3-uc-micro
}

customize_markdown-it-py() { ec "$1/debian/control" strip; }

customize_pygments() {
    local c="$1/debian/control" r="$1/debian/rules" py="$1/pyproject.toml"
    ec "$c" strip
    ec "$c" dropbin python-pygments-doc
    # without the doc package the doc build hook and its install line break
    sed -i '/^execute_after_dh_auto_build:/,+5d' "$r"
    sed -i '/test -d debian\/python-pygments-doc/d' "$r"
    # jammy's hatchling (0.15.0) predates PEP 639 string/list forms
    sed -i 's/^license = "\(.*\)"$/license = {text = "\1"}/' "$py"
    sed -i 's/^license-files = \[\(.*\)\]$/license-files = {globs = [\1]}/' "$py"
}

customize_python-typing-extensions() { ec "$1/debian/control" strip; }

customize_rich() {
    local c="$1/debian/control" r="$1/debian/rules"
    ec "$c" strip
    # rich 13.9.4 imports typing_extensions.Self (>= 4.0), but its control
    # accepts jammy's old 3.10 through the "| python3 (>> 3.8)" alternative
    ec "$c" replacedep python3-typing-extensions \
        "python3-typing-extensions (>= 4.0)"
    # the override runs pytest unconditionally, bypassing nocheck
    ec "$c" dropdeps python3-pytest python3-mypy
    # poetry-core's vendored packaging imports distutils.util, which lands in
    # setuptools._distutils.util; 78.1.1 pulls jaraco.functools (missing splat
    # in jammy), so pin the working 68.1.2 like the other consumers
    ec "$c" replacebd python3-setuptools "python3-setuptools (= $SETUPTOOLS_PIN)"
    sed -i '/PYBUILD_SYSTEM=custom.*dh_auto_test/d' "$r"
}

customize_fpdf2() {
    local c="$1/debian/control" r="$1/debian/rules"
    ec "$c" strip
    # Test-only build dependencies; the tests are disabled and the PPA
    # builders do not carry camelot/endesive/qrcode/pikepdf/qpdf.
    ec "$c" dropdeps camelot python3-endesive python3-qrcode python3-pytest \
        python3-pytest-cov python3-pikepdf qpdf
    # resolute's debhelper is compat 13; stonking has 14.
    if [ "$RELEASE" = resolute ]; then
        sed -i 's/debhelper-compat (= 14)/debhelper-compat (= 13)/' "$c"
    fi
    # the test override copies fixtures and runs dh_auto_test
    sed -i '/^override_dh_auto_test:/,$d' "$r"
}

customize_ocrmypdf() {
    local c="$1/debian/control" r="$1/debian/rules" py="$1/pyproject.toml" v="${1##*-}"
    # jammy setuptools-scm (6.4.2) cannot read git-archive versions; use static
    sed -i 's/^dynamic = \["version"\]/version = "'"$v"'"/' "$py"
    awk '/^\[/{skip = ($0 == "[tool.hatch.version]" || $0 == "[tool.hatch.build.hooks.vcs]")} !skip' "$py" > "$py.tmp" && mv "$py.tmp" "$py"
    sed -i 's/^from ocrmypdf\._version import __version__/__version__ = "'"$v"'"/' "$1/src/ocrmypdf/__init__.py"
    # _metadata.py imports ocrmypdf._version directly; the hatch-vcs hook
    # that would generate it was removed above, so write it out
    printf '__version__ = "%s"\n' "$v" > "$1/src/ocrmypdf/_version.py"
    # pydantic is not used by ocrmypdf 16.13 source; jammy has only 1.8.2.
    # 17.10 imports pydantic 2, so leave the dependency in place there.
    if [[ "$OCRMYPDF_VERSION" == 16.* ]]; then
        ec "$c" dropdeps python3-pydantic
    fi
    if [[ "$OCRMYPDF_VERSION" == 17.* ]]; then
        # 17.10's fpdf2 renderer calls TTFFont.escape_text (fpdf2 >= 2.8.9).
        # Use 2.8.9~ so the PPA's 2.8.9-0~ppaN versions satisfy it.
        ec "$c" replacedep python3-fpdf "python3-fpdf (>= 2.8.9~)"
    fi
    # ocrmypdf-doc needs sphinx-reredirects / sphinxcontrib-mermaid (absent)
    ec "$c" dropdeps python3-myst-parser python3-sphinx python3-sphinx-issues \
        python3-sphinx-reredirects python3-sphinx-rtd-theme \
        python3-sphinxcontrib-mermaid python3-pytest-runner
    ec "$c" dropbin ocrmypdf-doc
    # pin floors so jammy's old python3-pil (9.0.1) / rich (11.2.0) cannot
    # satisfy the dependency; jammy has no img2pdf or recent pdfminer at all
    ec "$c" replacedep python3-pil "python3-pil (>= 10.0.1)"
    ec "$c" replacedep python3-rich "python3-rich (>= 13)"
    ec "$c" replacedep python3-pdfminer "python3-pdfminer (>= 20220319)"
    ec "$c" replacedep python3-img2pdf "python3-img2pdf (>= 0.5)"
    sed -i 's/--with python3,sphinxdoc/--with python3/' "$r"
    sed -i '\|PYTHONPATH=debian/.debhelper sphinx-build docs html|d' "$r"
    sed -i '/^override_dh_sphinxdoc:/,+1d' "$r"
}

# ---------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------
fetch_source() {
    local name="$1" dir="$2" ver="$3" mirror="$4"
    local base src="$WORK/_src/$name"
    if [ -d "$src" ]; then
        cp -f "$src"/* .
        return 0
    fi
    if [ "$mirror" = ubuntu ]; then
        base="$MIRROR_UBUNTU/pool/$dir"
    else
        base="$MIRROR_DEBIAN/pool/$dir"
    fi
    [ -f "$name.dsc" ] || curl -fsSL -o "$name.dsc" "$base/${name}_${ver}.dsc"
    while read -r _ _ fname; do
        [ -z "$fname" ] && continue
        [ "$fname" = "$name.dsc" ] && continue
        [ -f "$fname" ] && continue
        curl -fsSL -o "$fname" "$base/$fname"
    done < <(awk '/^Files:/{flag=1; next} /^[A-Za-z]|^-----/{flag=0} flag {print}' "$name.dsc")
}

build_one() {
    local spec="$1"
    local name dir ver mirror
    IFS='|' read -r name dir ver mirror <<< "$spec"

    if [ -n "$ONLY" ] && [ "$name" != "$ONLY" ]; then
        return 0
    fi

    echo "=== $name $ver ==="
    local work="$WORK/$name"
    rm -rf "$work"
    mkdir -p "$work"
    ( cd "$work"
      fetch_source "$name" "$dir" "$ver" "$mirror"
      dpkg-source -x "$name.dsc" >/dev/null
      local extract
      extract=$(ls -d ./*/ | head -1 | sed 's#/$##')
      echo "  source: $extract"

      if declare -F "customize_$name" >/dev/null; then
          "customize_$name" "$PWD/$extract"
      fi
      disable_tests "$PWD/$extract"

      local dver upstream newver
      dver=$(awk '/^Version:/{print $2; exit}' "$name.dsc")
      if declare -F "ppa_version_$name" >/dev/null; then
          newver=$("ppa_version_$name" "$dver")
      else
          upstream=${dver%-*}
          newver="${upstream}-0~ppa${PPAREV}${RELEASE}"
      fi
      echo "  version: $newver"
      local changelog_msg="PPA build for $RELEASE"
      if declare -F "ppa_changelog_$name" >/dev/null; then
          changelog_msg=$("ppa_changelog_$name")
      fi
      ( cd "$extract"
        dch -v "$newver" -b --distribution "$RELEASE" "$changelog_msg"
        # record any upstream source edits as a proper Debian patch so
        # dpkg-source accepts the tree (3.0 quilt sources only)
        if [ -f debian/source/format ] && grep -qs '^3.0 (quilt)$' debian/source/format; then
            EDITOR=true VISUAL=true dpkg-source --commit . ppa-jammy
        fi
      )

      if [ "$DRY_RUN" = 1 ]; then
          echo "  [dry-run] skipping build"
          return 0
      fi

      if ! ( cd "$extract"; $BUILDER ); then
          echo "  !! build failed" >&2
          return 1
      fi
      mkdir -p "$WORK/out"
      mv "$work/${name}_${newver}"_source.changes \
         "$work/${name}_${newver}"_source.buildinfo \
         "$work/${name}_${newver}.dsc" \
         "$work/${name}_${newver}.debian.tar.xz" \
         "$work"/"${name}"_*.orig.tar.* \
         "$WORK/out/" 2>/dev/null || true
      echo "  -> $WORK/out/"
      if [ "$DO_UPLOAD" = 1 ]; then
          local changes
          changes="$WORK/out/${name}_${newver}_source.changes"
          if [ -n "$changes" ] && [ -f "$changes" ]; then
              dput "$PPA" "$changes"
          else
              echo "  !! no _source.changes found for $name" >&2
          fi
      fi
    ) || { echo "!! $name FAILED" >&2; return 1; }

    if [ "$KEEP" != 1 ] && [ "$DRY_RUN" != 1 ]; then
        rm -rf "$work"
    fi
}

started=0
for spec in "${PACKAGES[@]}"; do
    name="${spec%%|*}"
    if [ -n "$FROM" ]; then
        if [ "$started" = 0 ] && [ "$name" != "$FROM" ]; then
            continue
        fi
        started=1
    fi
    build_one "$spec" || true
done

echo "Done."
