"""Join the approved catalogs into the AppStream and desktop metadata.

Usage:
  python3 join_metadata.py --mo src/scantpaper/locale --out-dir build/generated
  python3 join_metadata.py --mo debian/locale --out-dir debian/generated

The input is the approval-gated .mo tree produced by compile_mo.py, not the
raw .po files, so the ledger is applied exactly once. Only gettext's msgunfmt
and msgfmt are required; itstool is not used.

msgfmt --xml reads the metainfo ITS rules installed on the system (it has no
--its option), so the script checks that they are present before it runs.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
DEFAULT_METAINFO = repo_root / "org.scantpaper.desktop.metainfo.xml"
DEFAULT_DESKTOP = repo_root / "org.scantpaper.desktop"

DESCRIPTION_RE = re.compile(r"<description>(.*?)</description>", re.DOTALL)
TAG_RE = re.compile(r"<\s*([A-Za-z][\w.:-]*)")
BLOCK_TAGS = frozenset({"li", "ol", "p", "ul"})
DESKTOP_UNTRANSLATED_KEYS = ("Name", "Keywords")
ITS_SEARCH_PATHS = (
    Path("/usr/share/gettext/its"),
    Path("/usr/local/share/gettext/its"),
    Path("/opt/homebrew/share/gettext/its"),
)


class JoinError(RuntimeError):
    """A metadata join that cannot produce valid output."""


@dataclass(frozen=True)
class JoinConfig:
    """The paths and domain for one metadata join."""

    mo_dir: Path
    out_dir: Path
    domain: str = "scantpaper"
    metainfo: Path = DEFAULT_METAINFO
    desktop: Path = DEFAULT_DESKTOP
    its_dir: Path | None = None


def find_catalogs(mo_dir: Path, domain: str) -> dict[str, Path]:
    """Return each language's compiled catalog under ``mo_dir``."""
    if not mo_dir.is_dir():
        msg = f"compiled catalog directory {mo_dir} does not exist"
        raise JoinError(msg)
    pattern = f"*/LC_MESSAGES/{domain}.mo"
    return {mo.parent.parent.name: mo for mo in sorted(mo_dir.glob(pattern))}


def find_its_dir(its_dir: Path | None) -> Path:
    """Return the directory holding the system metainfo ITS rules."""
    search = (its_dir,) if its_dir is not None else ITS_SEARCH_PATHS
    for candidate in search:
        if all(
            (candidate / name).is_file() for name in ("metainfo.its", "metainfo.loc")
        ):
            return candidate
    msg = (
        "no metainfo ITS rules found; install the AppStream package that "
        f"provides metainfo.its and metainfo.loc ({', '.join(str(p) for p in search)})"
    )
    raise JoinError(msg)


def check_no_inline_markup(metainfo: Path) -> None:
    """Reject description markup that ``msgfmt --xml`` would escape.

    Only block-level description elements are allowed. Any other tag inside
    ``<description>`` is inline markup, which ``msgfmt --xml`` would escape.
    """
    text = metainfo.read_text(encoding="utf-8")
    match = DESCRIPTION_RE.search(text)
    if match is None:
        return
    for tag_match in TAG_RE.finditer(match.group(1)):
        tag = tag_match.group(1)
        if tag not in BLOCK_TAGS:
            msg = (
                f"{metainfo.name} description has inline <{tag}> "
                "markup, which msgfmt --xml cannot preserve"
            )
            raise JoinError(msg)


def _capture(command: list[str], what: str) -> str:
    """Run one gettext command and return its standard output."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        msg = f"{what} could not run: {error}"
        raise JoinError(msg) from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        msg = f"{what} failed: {detail}"
        raise JoinError(msg)
    return result.stdout


def _run(command: list[str], what: str) -> None:
    """Run one gettext command, turning a failure into a JoinError."""
    _capture(command, what)


def unpack_catalogs(catalogs: dict[str, Path], tmp: Path) -> None:
    """Unpack every gated ``.mo`` file and write the ``LINGUAS`` list.

    A catalog with no approved translation contains only the header, which
    ``msgunfmt`` writes as empty output. Such a language contributes nothing,
    so it is left out of ``LINGUAS``.
    """
    languages: list[str] = []
    for language, mo in sorted(catalogs.items()):
        text = _capture(["msgunfmt", str(mo)], f"msgunfmt for {language}")
        if not text.strip():
            continue
        (tmp / f"{language}.po").write_text(text, encoding="utf-8")
        languages.append(language)
    (tmp / "LINGUAS").write_text(
        "".join(f"{language}\n" for language in languages), encoding="utf-8"
    )


def restore_desktop_keys(template: Path, output: Path) -> None:
    """Keep the template's ``Name`` and ``Keywords``, dropping localizations."""
    template_lines = template.read_text(encoding="utf-8").splitlines()
    kept = {
        line.split("=", 1)[0]: line
        for line in template_lines
        if line.split("=", 1)[0] in DESKTOP_UNTRANSLATED_KEYS
    }
    restored: list[str] = []
    placed: set[str] = set()
    for line in output.read_text(encoding="utf-8").splitlines():
        base = line.split("=", 1)[0].split("[", 1)[0]
        if base not in DESKTOP_UNTRANSLATED_KEYS:
            restored.append(line)
            continue
        if base in kept and base not in placed:
            restored.append(kept[base])
            placed.add(base)
    for key, line in kept.items():
        if key not in placed:
            restored.append(line)
    output.write_text("\n".join(restored) + "\n", encoding="utf-8")


def join(config: JoinConfig) -> None:
    """Write the joined metainfo and desktop entry into the output directory."""
    for template in (config.metainfo, config.desktop):
        if not template.is_file():
            msg = f"template {template} does not exist"
            raise JoinError(msg)
    find_its_dir(config.its_dir)
    check_no_inline_markup(config.metainfo)
    catalogs = find_catalogs(config.mo_dir, config.domain)

    config.out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="scantpaper-join-") as tmp_name:
        tmp = Path(tmp_name)
        unpack_catalogs(catalogs, tmp)
        _run(
            [
                "msgfmt",
                "--xml",
                f"--template={config.metainfo}",
                "-d",
                str(tmp),
                "-o",
                str(config.out_dir / config.metainfo.name),
            ],
            "msgfmt --xml",
        )
        _run(
            [
                "msgfmt",
                "--desktop",
                f"--template={config.desktop}",
                "-d",
                str(tmp),
                "-o",
                str(config.out_dir / config.desktop.name),
            ],
            "msgfmt --desktop",
        )
        restore_desktop_keys(config.desktop, config.out_dir / config.desktop.name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mo",
        type=Path,
        required=True,
        help="compiled locale tree produced by compile_mo.py",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="directory for the joined metainfo and desktop entry",
    )
    parser.add_argument(
        "--domain",
        default="scantpaper",
        help="gettext domain (default: scantpaper)",
    )
    parser.add_argument(
        "--metainfo",
        type=Path,
        default=DEFAULT_METAINFO,
        help="AppStream metainfo template",
    )
    parser.add_argument(
        "--desktop",
        type=Path,
        default=DEFAULT_DESKTOP,
        help="desktop entry template",
    )
    parser.add_argument(
        "--its-dir",
        type=Path,
        default=None,
        help="directory holding metainfo.its and metainfo.loc",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Join the metadata, returning an exit status."""
    args = parse_args(argv)
    try:
        join(
            JoinConfig(
                mo_dir=args.mo,
                out_dir=args.out_dir,
                domain=args.domain,
                metainfo=args.metainfo,
                desktop=args.desktop,
                its_dir=args.its_dir,
            )
        )
    except JoinError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
