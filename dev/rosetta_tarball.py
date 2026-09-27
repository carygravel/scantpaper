"""Package the template directory for Launchpad Rosetta upload.

Usage:
  python3 dev/rosetta_tarball.py          # -> scantpaper-po.tar.gz
  python3 dev/rosetta_tarball.py --out dist/scantpaper-po.tar.gz

Wraps the ``po/scantpaper/`` template directory (the generated pot plus one
``.po`` per language) into a tarball in the layout Rosetta expects, so it can
be uploaded as-is.
"""

from __future__ import annotations

import argparse
import sys
import tarfile
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent


def main() -> None:
    """Run the application entry point."""
    parser = argparse.ArgumentParser(description="Package the Rosetta template dir")
    parser.add_argument(
        "--src",
        type=Path,
        default=repo_root / "po" / "scantpaper",
        help="Template directory to package (default: po/scantpaper)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "scantpaper-po.tar.gz",
        help="Output tarball (default: scantpaper-po.tar.gz)",
    )
    args = parser.parse_args()

    src = Path(args.src)
    if not src.is_dir():
        print(f"Template directory '{src}' does not exist.", file=sys.stderr)
        sys.exit(1)
    pot = src / f"{src.name}.pot"
    if not pot.is_file():
        print(
            f"Template '{pot}' not found; run dev/generate_pot.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(out, "w:gz") as tf:
        tf.add(src, arcname=src.name)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
