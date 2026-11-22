"""Render every translated catalog through gettext.

`msgfmt --check` validates format flags but skips fuzzy entries and does not
execute the translation. This test compiles a de-fuzzed copy and formats every
message with arguments generated from its source placeholders, using the real
gettext lookup path. A Python ``%`` or ``str.format`` fault therefore fails
before an approval can ship it.

The temporary catalog is never written into ``po/``.
"""

from __future__ import annotations

import gettext
import re
import subprocess
from pathlib import Path

import polib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CATALOGS = REPO_ROOT / "po" / "scantpaper"

_PRINTF_TOKEN = re.compile(
    r"%(?:(?P<name>\([^)]+\))|(?P<position>\d+)\$)?"
    r"[-+ #0-9.*]*(?P<conv>[diouxXeEfgGaAcrspn])"
)
_FORMAT_FIELD = re.compile(r"(?<!\{)\{(?P<field>[^{}]*)\}(?!\})")


def _printf_value(conversion: str) -> object:
    """Return a value that can be formatted with one conversion letter."""
    if conversion in "diuoxX":
        return 1
    if conversion in "eEfFgG":
        return 1.0
    return "x"


def _format_value(spec: str) -> object:
    """Return a value that can be formatted with one format spec."""
    if spec and spec[-1] in "di":
        return 1
    if spec and spec[-1] in "eEfFgG%":
        return 1.0
    return "x"


def _format_message(message: str, source: str) -> str:
    """Format a translated message with arguments generated from its source."""
    printf = list(_PRINTF_TOKEN.finditer(source.replace("%%", "")))
    if printf:
        if any(match.group("name") for match in printf):
            mapping = {
                match.group("name")[1:-1]: _printf_value(match.group("conv"))
                for match in printf
            }
            return message % mapping
        args = tuple(_printf_value(match.group("conv")) for match in printf)
        return message % args

    fields = list(_FORMAT_FIELD.finditer(source))
    if not fields:
        return message

    positional: list[object] = []
    keywords: dict[str, object] = {}
    for match in fields:
        field = match.group("field")
        name, _, spec = field.partition(":")
        name = name.split("!", 1)[0].strip()
        value = _format_value(spec)
        if name == "":
            positional.append(value)
        elif name.isdigit():
            index = int(name)
            while len(positional) <= index:
                positional.append("x")
            positional[index] = value
        else:
            keywords[name] = value
    return message.format(*positional, **keywords)


def _render_catalog(path: Path, workdir: Path) -> list[str]:
    """Compile a de-fuzzed copy and return every rendering failure."""
    workdir.mkdir(parents=True, exist_ok=True)
    po = polib.pofile(str(path))
    for entry in po:
        if "fuzzy" in entry.flags:
            entry.flags.remove("fuzzy")
    temp_po = workdir / path.name
    po.save(str(temp_po))
    mo_path = workdir / f"{path.stem}.mo"
    subprocess.run(
        ["msgfmt", "-o", str(mo_path), str(temp_po)],
        check=True,
        capture_output=True,
        text=True,
    )

    errors: list[str] = []
    with mo_path.open("rb") as handle:
        translations = gettext.GNUTranslations(handle)
        for entry in po:
            if entry.obsolete or not entry.msgid:
                continue
            try:
                if entry.msgid_plural:
                    for count in (0, 1, 2, 5):
                        message = translations.ngettext(
                            entry.msgid, entry.msgid_plural, count
                        )
                        _format_message(message, entry.msgid_plural)
                else:
                    message = translations.gettext(entry.msgid)
                    _format_message(message, entry.msgid)
            except (KeyError, TypeError, ValueError) as error:
                errors.append(f"{path.name}: {entry.msgid!r}: {error}")
    return errors


def _write_catalog(path: Path, msgid: str, msgstr: str, *, fuzzy: bool = True) -> Path:
    """Write a one-entry catalog whose proposal may be fuzzy."""
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    }
    entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
    if fuzzy:
        entry.flags.append("fuzzy")
    po.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    po.save(str(path))
    return path


def test_render_check_catches_printf_mismatch(tmp_path: Path) -> None:
    """A translation whose conversion letter differs fails to render."""
    path = _write_catalog(tmp_path / "de.po", "Open file: %s", "Apri file: %d")
    errors = _render_catalog(path, tmp_path / "work")
    assert errors
    assert "Open file: %s" in errors[0]


def test_render_check_catches_renamed_format_field(tmp_path: Path) -> None:
    """A renamed str.format field fails at lookup time."""
    path = _write_catalog(tmp_path / "de.po", "{count} files", "{nombre} files")
    errors = _render_catalog(path, tmp_path / "work")
    assert errors
    assert "nombre" in errors[0]


def test_render_check_passes_a_matching_translation(tmp_path: Path) -> None:
    """A correctly formatted translation renders cleanly."""
    path = _write_catalog(
        tmp_path / "de.po", "Open file: %s", "Datei öffnen: %s", fuzzy=False
    )
    assert _render_catalog(path, tmp_path / "work") == []


def test_render_check_handles_bare_and_indexed_fields(tmp_path: Path) -> None:
    """Bare and indexed str.format fields are formatted with generated values."""
    bare = _write_catalog(tmp_path / "bare.po", "{} files", "{} Dateien")
    indexed = _write_catalog(tmp_path / "indexed.po", "{0} and {1}", "{1} und {0}")
    assert _render_catalog(bare, tmp_path / "bare-work") == []
    assert _render_catalog(indexed, tmp_path / "indexed-work") == []


def test_render_check_handles_format_specs(tmp_path: Path) -> None:
    """Integer and floating-point format specs get compatible values."""
    integer = _write_catalog(
        tmp_path / "integer.po", "{count:d} files", "{count:d} Dateien"
    )
    floating = _write_catalog(tmp_path / "float.po", "{ratio:.2f}%", "{ratio:.2f} %")
    assert _render_catalog(integer, tmp_path / "integer-work") == []
    assert _render_catalog(floating, tmp_path / "float-work") == []


def test_render_check_handles_named_printf(tmp_path: Path) -> None:
    """A named printf placeholder gets a mapping of generated values."""
    path = _write_catalog(tmp_path / "named.po", "%(count)d files", "%(count)d Dateien")
    assert _render_catalog(path, tmp_path / "named-work") == []


def test_render_check_clears_fuzzy_before_compiling(tmp_path: Path) -> None:
    """A fuzzy proposal is compiled and formatted, not skipped by msgfmt."""
    path = _write_catalog(
        tmp_path / "de.po", "Open file: %s", "Apri file: %d", fuzzy=True
    )
    assert _render_catalog(path, tmp_path / "work")


def test_render_check_handles_plural_forms(tmp_path: Path) -> None:
    """Every plural form is formatted through the gettext lookup path."""
    path = tmp_path / "plural.po"
    po = polib.POFile()
    po.metadata = {
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": "nplurals=2; plural=(n != 1);",
    }
    po.append(
        polib.POEntry(
            msgid="%d file",
            msgid_plural="%d files",
            msgstr_plural={0: "%d Datei", 1: "%d Dateien"},
        )
    )
    po.save(str(path))
    assert _render_catalog(path, tmp_path / "work") == []


def test_every_committed_catalog_renders(tmp_path: Path) -> None:
    """Every message in every shipped catalog formats with its own arguments."""
    errors: list[str] = []
    for path in sorted(CATALOGS.glob("*.po")):
        errors.extend(_render_catalog(path, tmp_path / path.stem))
    assert errors == []
