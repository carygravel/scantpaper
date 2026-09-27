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
    tmp_path: Path,
    body: str,
    lang: str = "de",
    pot_msgids: tuple[str, ...] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Write a one-entry catalog for ``lang`` and run check_po.py over it.

    ``pot_msgids`` writes a synthetic message template and passes it with
    ``--pot``, so the source-side checks can be driven from a known msgid set
    instead of whatever the tree currently contains. Pass ``()`` to isolate a
    catalog check from the source checks; leave it ``None`` to use the real
    source.
    """
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

    command = [
        "python3",
        str(REPO_ROOT / "dev" / "check_po.py"),
        "--src",
        str(src),
    ]
    if pot_msgids is not None:
        pot = tmp_path / "synthetic.pot"
        entries = "".join(f'msgid "{m}"\nmsgstr ""\n\n' for m in pot_msgids)
        pot.write_text(
            'msgid ""\n'
            'msgstr ""\n'
            '"MIME-Version: 1.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            "\n" + entries,
            encoding="utf-8",
        )
        command += ["--pot", str(pot)]

    return subprocess.run(command, capture_output=True, text=True, check=False)


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
    result = _run_check_po(tmp_path, body, pot_msgids=())
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
    result = _run_check_po(tmp_path, body, pot_msgids=())
    assert result.returncode == 0, result.stdout


def test_bare_multifield_is_advisory(tmp_path: Path) -> None:
    """A bare multi-field str.format msgid warns without failing."""
    body = 'msgid "{} and {}"\nmsgstr "{} und {}"\n'
    result = _run_check_po(tmp_path, body, pot_msgids=())
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


def test_plural_hack_msgid_fails(tmp_path: Path) -> None:
    """A msgid with a parenthesised plural suffix is rejected."""
    result = _run_check_po(tmp_path, "", pot_msgids=("Open image file(s)",))
    assert result.returncode != 0
    assert "plural hack" in result.stdout


def test_plural_hack_es_msgid_fails(tmp_path: Path) -> None:
    """The Spanish plural suffix is caught by the same rule."""
    result = _run_check_po(tmp_path, "", pot_msgids=("Guardar documento(s)",))
    assert result.returncode != 0
    assert "plural hack" in result.stdout


def test_plural_hack_needs_a_preceding_word_character(tmp_path: Path) -> None:
    """A parenthesised suffix with no preceding word character is not flagged."""
    result = _run_check_po(tmp_path, "", pot_msgids=("(s)",))
    assert result.returncode == 0, result.stdout


def test_parenthesised_unit_and_gloss_pass(tmp_path: Path) -> None:
    """A parenthesised unit, abbreviation or gloss is not a plural hack."""
    result = _run_check_po(
        tmp_path,
        "",
        pot_msgids=(
            "Warn if available space less than (Mb)",
            "Compress output with JPEG (DCT) encoding.",
            "Device blacklist (regular expression)",
            "Use LibTIFF (tiff2ps) to create Postscript files from TIFF.",
        ),
    )
    assert result.returncode == 0, result.stdout


def test_msgstr_copied_from_another_msgid_is_advisory(tmp_path: Path) -> None:
    """A msgstr equal to a different msgid is reported without failing."""
    body = (
        'msgid "Select Odd"\n'
        'msgstr "Selected"\n'
        "\n"
        'msgid "Selected"\n'
        'msgstr "Ausgewahlt"\n'
    )
    result = _run_check_po(tmp_path, body, pot_msgids=())
    assert result.returncode == 0, result.stdout
    assert "which is a different msgid" in result.stdout


def test_msgstr_matching_own_msgid_case_only_is_not_reported(tmp_path: Path) -> None:
    """A msgstr differing from its own msgid only by case is not a mismatch."""
    body = 'msgid "_Ok"\nmsgstr "_OK"\n\nmsgid "_OK"\nmsgstr "_OK"\n'
    result = _run_check_po(tmp_path, body, pot_msgids=())
    assert result.returncode == 0, result.stdout
    assert "which is a different msgid" not in result.stdout


def test_siblings_sharing_a_translation_are_advisory(tmp_path: Path) -> None:
    """Two sibling controls given one translation are reported."""
    body = (
        'msgid "Select Odd"\n'
        'msgstr "Ausgewahlt"\n'
        "\n"
        'msgid "Select Even"\n'
        'msgstr "Ausgewahlt"\n'
    )
    result = _run_check_po(tmp_path, body, pot_msgids=())
    assert result.returncode == 0, result.stdout
    assert "share the translation" in result.stdout


def test_distinct_sibling_translations_pass(tmp_path: Path) -> None:
    """Siblings with distinct translations are not reported."""
    body = (
        'msgid "Select Odd"\n'
        'msgstr "Ungerade wahlen"\n'
        "\n"
        'msgid "Select Even"\n'
        'msgstr "Gerade wahlen"\n'
    )
    result = _run_check_po(tmp_path, body, pot_msgids=())
    assert result.returncode == 0, result.stdout
    assert "share the translation" not in result.stdout


def test_case_only_duplicate_msgids_are_advisory(tmp_path: Path) -> None:
    """Two msgids differing only by case are reported."""
    result = _run_check_po(tmp_path, "", pot_msgids=("Scan Options", "Scan options"))
    assert result.returncode == 0, result.stdout
    assert "differ only by case" in result.stdout


def test_concatenation_fragment_is_advisory(tmp_path: Path) -> None:
    """A msgid ending in a colon with no value is reported as a fragment."""
    result = _run_check_po(tmp_path, "", pot_msgids=("Error opening device: ",))
    assert result.returncode == 0, result.stdout
    assert "concatenation fragment" in result.stdout


def test_fragment_ending_in_bare_colon_is_advisory(tmp_path: Path) -> None:
    """A fragment is detected whether or not a space follows the colon."""
    result = _run_check_po(
        tmp_path,
        "",
        pot_msgids=("The following paper sizes are too big by the device:",),
    )
    assert result.returncode == 0, result.stdout
    assert "concatenation fragment" in result.stdout


def test_self_contained_string_ending_in_colon_is_not_a_fragment(
    tmp_path: Path,
) -> None:
    """A colon-terminated string that carries its own value is not reported."""
    result = _run_check_po(
        tmp_path, "", pot_msgids=("Error on %s: device busy", "{0} and {1}:")
    )
    assert result.returncode == 0, result.stdout
    assert "concatenation fragment" not in result.stdout


def test_doubled_space_is_advisory(tmp_path: Path) -> None:
    """A msgid with a doubled space is reported."""
    result = _run_check_po(
        tmp_path, "", pot_msgids=("The size is too big.  Please save fewer.",)
    )
    assert result.returncode == 0, result.stdout
    assert "contains a doubled space" in result.stdout


def test_greek_mu_is_advisory(tmp_path: Path) -> None:
    """A msgid using GREEK SMALL LETTER MU is reported."""
    result = _run_check_po(tmp_path, "", pot_msgids=("μs",))
    assert result.returncode == 0, result.stdout
    assert "GREEK SMALL LETTER MU" in result.stdout


def test_over_long_msgid_is_advisory(tmp_path: Path) -> None:
    """A msgid over 200 characters is reported as a translation effort risk."""
    result = _run_check_po(tmp_path, "", pot_msgids=("x" * 201,))
    assert result.returncode == 0, result.stdout
    assert "translation effort risk" in result.stdout


def test_msgid_at_the_length_limit_is_not_reported(tmp_path: Path) -> None:
    """A msgid of exactly 200 characters is not reported."""
    result = _run_check_po(tmp_path, "", pot_msgids=("x" * 200,))
    assert result.returncode == 0, result.stdout
    assert "translation effort risk" not in result.stdout


def test_label_and_tooltip_pair_is_not_reported(tmp_path: Path) -> None:
    """A label and its punctuated tooltip are not reported as near-duplicates."""
    result = _run_check_po(tmp_path, "", pot_msgids=("Both sides", "Both sides."))
    assert result.returncode == 0, result.stdout
    for condition in (
        "differ only by case",
        "concatenation fragment",
        "contains a doubled space",
        "translation effort risk",
    ):
        assert condition not in result.stdout
