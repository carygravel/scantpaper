#!/usr/bin/env python3
"""
Compile .po files into .mo files.

Usage:
  python3 compile_mo.py # compiles po/*.po into locale/<lang>/LC_MESSAGES/<domain>.mo
  python3 compile_mo.py --src po --out locale
  python3 compile_mo.py --src po --out locale --domain scantpaper
"""
from pathlib import Path
import argparse
import sys
import polib


def guess_lang_and_domain(po_file: Path, given_domain: str = None):
    """Try to infer language and domain from filename:
    common forms:
       <domain>-<lang>.po  -> domain, lang
       <lang>.po           -> domain from given_domain, lang"""
    name = po_file.name
    if name.count("-") >= 1 and name.endswith(".po"):
        # Try domain-lang.po -> split last '-' occurrence
        base = name[:-3]  # strip .po
        parts = base.rsplit("-", 1)
        if len(parts) == 2 and parts[1]:
            domain, lang = parts[0], parts[1]
            return domain if given_domain is None else given_domain, lang
    # fallback: name without extension is lang
    lang = name[:-3]
    domain = given_domain or "messages"
    return domain, lang


def main():
    "main"
    p = argparse.ArgumentParser(description="Compile .po to .mo")
    p.add_argument(
        "--src", default="po", help="Source dir containing .po files (default: po)"
    )
    p.add_argument(
        "--out", default="locale", help="Output locale dir (default: locale)"
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
        domain, lang = guess_lang_and_domain(po, args.domain)
        mo_path = Path(args.out) / lang / "LC_MESSAGES" / f"{domain}.mo"
        print(f"Compiling {po} -> {mo_path} (domain={domain}, lang={lang})")
        mo_path.parent.mkdir(parents=True, exist_ok=True)
        po = polib.pofile(str(po_path))
        po.save_as_mofile(str(mo_path))


if __name__ == "__main__":
    main()
