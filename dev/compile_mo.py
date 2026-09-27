"""Compile .po files into .mo files.

Usage:
  python3 compile_mo.py # compiles po/scantpaper/*.po into src/scantpaper/locale/<lang>/LC_MESSAGES/<domain>.mo
  python3 compile_mo.py --src po/scantpaper --out src/scantpaper/locale
  python3 compile_mo.py --src po/scantpaper --out src/scantpaper/locale --domain scantpaper
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polib


def guess_lang_and_domain(
    po_file: Path, given_domain: str | None = None
) -> tuple[str, str]:
    """Infer language and domain from a Rosetta-layout file path.

    A template directory holds one template's files, so the directory name is
    the domain and the file stem is the language, e.g. ``po/scantpaper/de.po``
    -> domain ``scantpaper``, language ``de``. ``given_domain`` overrides the
    domain when supplied.
    """
    lang = po_file.stem
    domain = given_domain or po_file.parent.name
    return domain, lang


def main() -> None:
    """Run the application entry point."""
    p = argparse.ArgumentParser(description="Compile .po to .mo")
    p.add_argument(
        "--src",
        default="po/scantpaper",
        help="Source dir containing .po files (default: po/scantpaper)",
    )
    p.add_argument(
        "--out",
        default="src/scantpaper/locale",
        help="Output locale dir (default: src/scantpaper/locale)",
    )
    p.add_argument(
        "--domain",
        default=None,
        help="Force domain for output (default: inferred from filename or 'messages')",
    )
    p.add_argument(
        "--pattern",
        default="*.po",
        help="Glob pattern for .po files under --src (default: *.po)",
    )
    args = p.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"Source dir '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)

    po_files = list(src.rglob(args.pattern))
    if not po_files:
        print("No .po files found.", file=sys.stderr)
        sys.exit(0)

    for po_path in po_files:
        domain, lang = guess_lang_and_domain(po_path, args.domain)
        mo_path = Path(args.out) / lang / "LC_MESSAGES" / f"{domain}.mo"
        print(f"Compiling {po_path} -> {mo_path} (domain={domain}, lang={lang})")
        mo_path.parent.mkdir(parents=True, exist_ok=True)
        po = polib.pofile(str(po_path))
        po.save_as_mofile(str(mo_path))


if __name__ == "__main__":
    main()
