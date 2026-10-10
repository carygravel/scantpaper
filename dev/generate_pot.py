"""Create pot for translation strings. Requires gettext."""

from __future__ import annotations

import argparse
import datetime
import os
import subprocess
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
pkg_dir = repo_root / "src" / "scantpaper"
its_rules = Path(__file__).resolve().parent / "gtkbuilder.its"
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
        os.chdir(pkg_dir)
        ui_sources = sorted(str(x) for x in Path().rglob("*.ui"))
        py_sources = sorted(str(x) for x in Path().rglob("*.py"))

        py_pot = "_py_tmp.pot"
        subprocess.run(
            [
                "xgettext",
                "--language=Python",
                "--from-code=UTF-8",
                "-o",
                py_pot,
                "--keyword=_",
                "--keyword=N_",
                *py_sources,
            ],
            check=True,
        )

        tmp_pots = [py_pot]
        if ui_sources:
            # A Glade .ui file is GtkBuilder XML, so gettext's own ITS rules
            # for GtkBuilder describe which attributes are translatable. The
            # rules are vendored beside this script so that the msgid set does
            # not depend on the gettext version or install layout of whichever
            # machine generates the template; see dev/its-rules.md.
            ui_pot = "_ui_tmp.pot"
            subprocess.run(
                [
                    "xgettext",
                    f"--its={its_rules}",
                    "--from-code=UTF-8",
                    "-o",
                    ui_pot,
                    *ui_sources,
                ],
                check=True,
            )
            tmp_pots.append(ui_pot)

        out = subprocess.check_output(["msgcat", "--use-first", *tmp_pots], text=True)
        for x in tmp_pots:
            Path(x).unlink(missing_ok=True)
    finally:
        os.chdir(previous_cwd)

    local_tz = datetime.datetime.now().astimezone().tzinfo
    year = datetime.datetime.now(local_tz).year
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
