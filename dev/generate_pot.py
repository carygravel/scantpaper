"Create pot for translation strings. Requires intltool package"

from pathlib import Path
import subprocess
import glob
from contextlib import chdir
import os
import sys
import datetime

root = Path(__file__).resolve().parents[1] / "scantpaper"
sys.path.insert(0, str(root))
from const import (  # pylint: disable=wrong-import-position,import-error
    PROG_NAME as NAME,
    VERSION,
    AUTHOR,
    AUTHOR_EMAIL as EMAIL,
)


def main():
    "main"
    with chdir(root):
        ui_sources = glob.glob("**/*.ui", recursive=True)
        for x in ui_sources:
            subprocess.run(["intltool-extract", "--type=gettext/glade", x], check=True)
        uih_sources = [x + ".h" for x in ui_sources]
        py_sources = glob.glob("**/*.py", recursive=True)
        out = subprocess.check_output(
            [
                "pygettext3",
                "-o",
                "-",
                "-kN_",
                "-k_",
            ]
            + uih_sources
            + py_sources,
            text=True,
        )
        for x in uih_sources:
            os.remove(x)

    year = datetime.datetime.today().year
    out = (
        out.replace("SOME DESCRIPTIVE TITLE", f"messages.pot for {NAME}", 1)
        .replace("PACKAGE VERSION", f"{NAME}-{VERSION}", 1)
        .replace("YEAR THE PACKAGE'S COPYRIGHT HOLDER", f"{year} {AUTHOR}", 1)
        .replace("PACKAGE", NAME, 1)
        .replace("FIRST AUTHOR <EMAIL@ADDRESS>, YEAR", f"{AUTHOR} <{EMAIL}>, {year}", 1)
        .replace("Report-Msgid-Bugs-To: ", f"Report-Msgid-Bugs-To: {EMAIL}", 1)
    )
    filename = NAME + ".pot"
    with open(filename, "wt", encoding="utf-8") as fhd:
        fhd.write(out)
    print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
