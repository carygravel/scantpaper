"""Create pot for translation strings. Requires gettext."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import tempfile
from pathlib import Path

import polib

repo_root = Path(__file__).resolve().parent.parent
pkg_dir = repo_root / "src" / "scantpaper"
its_rules = Path(__file__).resolve().parent / "gtkbuilder.its"
metainfo_rules = Path(__file__).resolve().parent / "metainfo.its"
metainfo_source = repo_root / "org.scantpaper.desktop.metainfo.xml"
desktop_source = repo_root / "org.scantpaper.desktop"
EXCLUDED_DESKTOP_KEYS = frozenset({"Name", "Keywords"})
from scantpaper.const import (  # noqa: E402
    AUTHOR,
    VERSION,
)
from scantpaper.const import (  # noqa: E402
    AUTHOR_EMAIL as EMAIL,
)
from scantpaper.const import (  # noqa: E402
    PROG_NAME as NAME,
)


def _prepare_desktop_source(source: Path, destination: Path) -> None:
    """Copy a desktop entry with its untranslatable keys renamed.

    Renaming ``Name`` and ``Keywords`` keeps every line in place, so the
    references xgettext records still point at the right line of the real
    source, while the Desktop parser no longer extracts their values.
    """
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    renamed: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip()
        renamed.append(f"X-Scantpaper-{line}" if key in EXCLUDED_DESKTOP_KEYS else line)
    destination.write_text("".join(renamed), encoding="utf-8")


def _rewrite_desktop_occurrences(pot: Path, temporary: str, source_name: str) -> None:
    """Point the desktop references at the real source file."""
    parsed = polib.pofile(str(pot))
    for entry in parsed:
        entry.occurrences = [
            (source_name if name == temporary else name, line)
            for name, line in entry.occurrences
        ]
    parsed.save(str(pot))


def generate_template() -> str:
    """Extract the message template from the source tree and return its text.

    ``gettext`` (xgettext and msgcat) is the only external tool required. The
    caller is responsible for writing the returned template where it wants it;
    the CLI writes it to the default path (see ``main``).
    """
    # contextlib.chdir needs Python 3.11, but the minimum supported version
    # (see requires-python) is 3.10, so change directory by hand and always
    # restore it before returning the template.
    previous_cwd = Path.cwd()
    try:
        # The metadata rules and sources live at the repository root, so run
        # there: xgettext then records relative references such as
        # ``org.scantpaper.desktop.metainfo.xml:10``.
        os.chdir(repo_root)
        metainfo_pot = repo_root / "_metainfo_tmp.pot"
        subprocess.run(
            [
                "xgettext",
                f"--its={metainfo_rules}",
                "--from-code=UTF-8",
                "-o",
                str(metainfo_pot),
                metainfo_source.name,
            ],
            check=True,
        )

        desktop_pot = repo_root / "_desktop_tmp.pot"
        with tempfile.TemporaryDirectory(prefix="scantpaper-desktop-") as tmp_name:
            desktop_copy = Path(tmp_name) / desktop_source.name
            _prepare_desktop_source(desktop_source, desktop_copy)
            subprocess.run(
                [
                    "xgettext",
                    "--language=Desktop",
                    "--from-code=UTF-8",
                    "-o",
                    str(desktop_pot),
                    str(desktop_copy),
                ],
                check=True,
            )
            _rewrite_desktop_occurrences(
                desktop_pot, str(desktop_copy), desktop_source.name
            )

        os.chdir(pkg_dir)
        ui_sources = sorted(str(x) for x in Path().rglob("*.ui"))
        py_sources = sorted(str(x) for x in Path().rglob("*.py"))

        py_pot = Path("_py_tmp.pot")
        subprocess.run(
            [
                "xgettext",
                "--language=Python",
                "--from-code=UTF-8",
                "-o",
                str(py_pot),
                "--keyword=_",
                "--keyword=N_",
                *py_sources,
            ],
            check=True,
        )

        tmp_pots = [metainfo_pot, desktop_pot, py_pot]
        if ui_sources:
            # A Glade .ui file is GtkBuilder XML, so gettext's own ITS rules
            # for GtkBuilder describe which attributes are translatable. The
            # rules are vendored beside this script so that the msgid set does
            # not depend on the gettext version or install layout of whichever
            # machine generates the template; see dev/its-rules.md.
            ui_pot = Path("_ui_tmp.pot")
            subprocess.run(
                [
                    "xgettext",
                    f"--its={its_rules}",
                    "--from-code=UTF-8",
                    "-o",
                    str(ui_pot),
                    *ui_sources,
                ],
                check=True,
            )
            tmp_pots.append(ui_pot)

        # No --use-first: both inputs are templates with empty msgstr, and the
        # flag would discard the second entry's references for a shared msgid.
        out = subprocess.check_output(
            ["msgcat", *(str(x) for x in tmp_pots)], text=True
        )
        for x in tmp_pots:
            x.unlink(missing_ok=True)
    finally:
        os.chdir(previous_cwd)

    local_tz = dt.datetime.now().astimezone().tzinfo
    year = dt.datetime.now(local_tz).year
    return (
        out.replace("SOME DESCRIPTIVE TITLE", f"messages.pot for {NAME}", 1)
        .replace("PACKAGE VERSION", f"{NAME}-{VERSION}", 1)
        .replace("YEAR THE PACKAGE'S COPYRIGHT HOLDER", f"{year} {AUTHOR}", 1)
        .replace("PACKAGE", NAME, 1)
        .replace("FIRST AUTHOR <EMAIL@ADDRESS>, YEAR", f"{AUTHOR} <{EMAIL}>, {year}", 1)
        .replace("Report-Msgid-Bugs-To: ", f"Report-Msgid-Bugs-To: {EMAIL}", 1)
    )


def main() -> None:
    """Generate and write the POT template, printing the output path."""
    parser = argparse.ArgumentParser(description="Generate the POT template")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write the template here (default: po/scantpaper/scantpaper.pot)",
    )
    args = parser.parse_args()
    output = args.output or repo_root / "po" / "scantpaper" / (NAME + ".pot")
    out = generate_template()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fhd:
        fhd.write(out)
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
