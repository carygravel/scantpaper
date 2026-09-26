"""Tests for compiling and validating translation .po files."""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

_PLURAL_FORMS = {
    "de": "nplurals=2; plural=(n != 1);",
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : "
    "n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
}


def _run_check_po(
    tmp_path: Path, body: str, lang: str = "de"
) -> subprocess.CompletedProcess[str]:
    """Write a one-entry catalog for ``lang`` and run check_po.py over it."""
    src = tmp_path / "po"
    src.mkdir()
    header = (
        'msgid ""\n'
        'msgstr ""\n'
        '"MIME-Version: 1.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        f'"Language: {lang}\\n"\n'
        f'"Plural-Forms: {_PLURAL_FORMS[lang]}\\n"\n'
    )
    (src / f"scantpaper-{lang}.po").write_text(header + body, encoding="utf-8")
    return subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "dev" / "check_po.py"),
            "--src",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_compile_po_files(tmp_path: Path) -> None:
    """All .po files compile cleanly to .mo, as done in CI."""
    src = REPO_ROOT / "po"
    out = tmp_path / "locale"

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "dev" / "compile_mo.py"),
            "--src",
            str(src),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_check_po_files() -> None:
    """All .po files pass deterministic catalog checks, as done in CI."""
    src = REPO_ROOT / "po"

    result = subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "dev" / "check_po.py"),
            "--src",
            str(src),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_split_printf_token_fails(tmp_path: Path) -> None:
    """A printf token split from its letter by a space is rejected."""
    body = '#, python-format\nmsgid "Open file: %s"\nmsgstr "Apri file:% s"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode != 0
    assert "printf token split by space" in result.stdout


def test_positional_reorder_passes(tmp_path: Path) -> None:
    """Legitimate printf positional reordering is accepted."""
    body = '#, python-format\nmsgid "%1$d of %2$d"\nmsgstr "%2$d di %1$d"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode == 0, result.stdout


def test_renamed_format_field_fails(tmp_path: Path) -> None:
    """A str.format field whose name changed is rejected."""
    body = 'msgid "{count} files in {dir}"\nmsgstr "{ count } files in {dir}"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode != 0
    assert "str.format fields changed" in result.stdout


def test_malformed_brace_fails(tmp_path: Path) -> None:
    """An unbalanced brace in a str.format translation is rejected."""
    body = 'msgid "value: {x}"\nmsgstr "valore: {x"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode != 0
    assert "malformed braces" in result.stdout


def test_matching_format_fields_pass(tmp_path: Path) -> None:
    """Reordered indexed fields with matching names are accepted."""
    body = 'msgid "{0} and {1}"\nmsgstr "{1} et {0}"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode == 0, result.stdout


def test_bare_multifield_is_advisory(tmp_path: Path) -> None:
    """A bare multi-field str.format msgid warns without failing."""
    body = 'msgid "{} and {}"\nmsgstr "{} und {}"\n'
    result = _run_check_po(tmp_path, body)
    assert result.returncode == 0, result.stdout
    assert "bare-multifield" in result.stdout


def test_obsolete_growth_fails(tmp_path: Path) -> None:
    """Obsolete entries beyond a catalog's ceiling fail the build."""
    # ru's ceiling is 139; emit 140 obsolete entries.
    obsolete = "".join(
        f'#~ msgid "gone {i}"\n#~ msgstr "weg {i}"\n\n' for i in range(140)
    )
    result = _run_check_po(tmp_path, obsolete, lang="ru")
    assert result.returncode != 0
    assert "exceeds ceiling" in result.stdout
