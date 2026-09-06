"""Create pot for translation strings. Requires intltool package."""

import datetime
import subprocess
from contextlib import chdir
from pathlib import Path

pkg_dir = Path(__file__).resolve().parents[1] / "src" / "scantpaper"
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


def main():
    """Run the application entry point."""
    with chdir(pkg_dir):
        ui_sources = sorted(str(x) for x in Path().rglob("*.ui"))
        for x in ui_sources:
            subprocess.run(["intltool-extract", "--type=gettext/glade", x], check=True)
        uih_sources = [x + ".h" for x in ui_sources]
        py_sources = sorted(str(x) for x in Path().rglob("*.py"))
        out = subprocess.check_output(
            ["pygettext3", "-o", "-", "-kN_", "-k_", *uih_sources, *py_sources],
            text=True,
        )
        for x in uih_sources:
            Path(x).unlink()

    local_tz = datetime.datetime.now().astimezone().tzinfo
    year = datetime.datetime.now(local_tz).year
    out = (
        out.replace("SOME DESCRIPTIVE TITLE", f"messages.pot for {NAME}", 1)
        .replace("PACKAGE VERSION", f"{NAME}-{VERSION}", 1)
        .replace("YEAR THE PACKAGE'S COPYRIGHT HOLDER", f"{year} {AUTHOR}", 1)
        .replace("PACKAGE", NAME, 1)
        .replace("FIRST AUTHOR <EMAIL@ADDRESS>, YEAR", f"{AUTHOR} <{EMAIL}>, {year}", 1)
        .replace("Report-Msgid-Bugs-To: ", f"Report-Msgid-Bugs-To: {EMAIL}", 1)
    )
    filename = NAME + ".pot"
    with Path(filename).open("w", encoding="utf-8") as fhd:
        fhd.write(out)
    print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
