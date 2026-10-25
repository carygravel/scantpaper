"""Remove remote images from the generated HTML documentation.

Lintian's ``privacy-breach-*`` checks flag documentation that makes a
reader's browser fetch an image from a third-party host. The README embeds
project badges and a donation button, so the generated HTML is sanitised
here instead of carrying lintian overrides that would hide the finding.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Final

IMAGE: Final = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
REMOTE_SOURCE: Final = re.compile(r'\bsrc\s*=\s*"(?:https?:)?//', re.IGNORECASE)


def strip_remote_images(html: str) -> str:
    """Remove image elements whose source is absolute or protocol-relative."""
    return IMAGE.sub(
        lambda match: "" if REMOTE_SOURCE.search(match.group(0)) else match.group(0),
        html,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="HTML file to sanitise in place")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Sanitise the file in place, returning a process exit status."""
    args = parse_args(argv)
    try:
        text = args.path.read_text(encoding="utf-8")
        args.path.write_text(strip_remote_images(text), encoding="utf-8")
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
