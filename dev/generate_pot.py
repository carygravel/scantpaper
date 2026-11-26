"""Create pot for translation strings. Requires gettext."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
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


def _desktop_line_keys(source: Path) -> dict[str, str]:
    """Map gettext's desktop reference line numbers to entry keys.

    gettext's Desktop parser reports the line after the key/value line, so the
    reported number is one greater than the 1-based line number in the file.
    """
    keys: dict[str, str] = {}
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        keys[str(number + 1)] = line.split("=", 1)[0]
    return keys


def _filter_desktop_pot(pot: Path, source: Path) -> None:
    """Remove entries extracted only from untranslatable desktop keys.

    The filter looks at the line each occurrence points to rather than at the
    msgid, so a translatable ``Comment`` that happens to share its text with
    the brand or the keyword list is kept.
    """
    keys = _desktop_line_keys(source)
    parsed = polib.pofile(str(pot))
    for entry in list(parsed):
        if not entry.occurrences:
            continue
        if all(
            keys.get(line) in EXCLUDED_DESKTOP_KEYS for _, line in entry.occurrences
        ):
            parsed.remove(entry)
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
        subprocess.run(
            [
                "xgettext",
                "--language=Desktop",
                "--from-code=UTF-8",
                "-o",
                str(desktop_pot),
                desktop_source.name,
            ],
            check=True,
        )
        _filter_desktop_pot(desktop_pot, desktop_source)

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
