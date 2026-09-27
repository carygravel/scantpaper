"""Tests for compiling and validating translation .po files."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import polib

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


# Msgids that exist only in the .ui files, so finding them proves the ITS
# extraction ran. If the rules cannot be resolved, xgettext silently extracts
# nothing from the three .ui files and every source-side check would then
# report a clean result over a set missing 83 user-interface strings.
_UI_ONLY_MSGIDS = (
    "Attach as PDF to a new email",
    "Clear OCR",
    "Clears all pages",
    "Copy selection",
    "Crop selection",
    "Cut selection",
    "Edit annotations",
    "Invert selection",
    "Open images",
    "Paste selection",
    "Prefere_nces",
)

# The number of msgids the three .ui files contribute, measured on 2026-09-27
# with gettext 1.0. Asserted as a floor rather than an equality: the point is
# to catch the extraction collapsing to nothing, not to make every new
# translatable string a test failure.
_UI_MSGID_FLOOR = 83

_VENDORED_ITS = REPO_ROOT / "dev" / "gtkbuilder.its"


def _run_generate_pot(
    tmp_path: Path, path: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run dev/generate_pot.py and return the result.

    ``path`` replaces ``PATH`` for the run, so a test can present the
    generator with only the tools it is entitled to need. The template is
    written into ``tmp_path`` rather than the repository.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    ).rstrip(os.pathsep)
    if path is not None:
        env["PATH"] = str(path)
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "dev" / "generate_pot.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _gettext_only_path(tmp_path: Path) -> Path:
    """Build a PATH directory holding gettext's tools and nothing else.

    ``intltool-extract`` is deliberately absent, which is the situation this
    change removes the need for.
    """
    bindir = tmp_path / "gettext-bin"
    bindir.mkdir()
    for tool in ("python3", "xgettext", "msgcat", "msgfmt"):
        found = shutil.which(tool)
        assert found is not None, f"{tool} is not installed"
        (bindir / tool).symlink_to(found)
    return bindir


def test_generate_pot_needs_no_intltool(tmp_path: Path) -> None:
    """The template is generated with gettext alone, with no intltool."""
    result = _run_generate_pot(tmp_path, path=_gettext_only_path(tmp_path))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "intltool" not in (result.stdout + result.stderr)
    pot = polib.pofile(str(tmp_path / "scantpaper.pot"))
    msgids = {entry.msgid for entry in pot if entry.msgid}
    for msgid in _UI_ONLY_MSGIDS:
        assert msgid in msgids, f"{msgid!r} missing from the generated template"


def test_ui_msgids_are_extracted_from_the_ui_files(tmp_path: Path) -> None:
    """The .ui contribution to the template is not silently empty."""
    result = _run_generate_pot(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    pot = polib.pofile(str(tmp_path / "scantpaper.pot"))
    msgids = {entry.msgid for entry in pot if entry.msgid}
    for msgid in _UI_ONLY_MSGIDS:
        assert msgid in msgids, f"{msgid!r} missing from the generated template"


def test_ui_msgid_count_has_not_collapsed(tmp_path: Path) -> None:
    """The .ui files still contribute at least the msgids they used to."""
    result = _run_generate_pot(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    src = REPO_ROOT / "src" / "scantpaper"
    env = dict(os.environ)
    env["PATH"] = (
        _gettext_only_path(tmp_path).as_posix() + os.pathsep + os.environ["PATH"]
    )
    ui_pot = tmp_path / "ui-only.pot"
    subprocess.run(
        [
            "xgettext",
            f"--its={_VENDORED_ITS}",
            "--from-code=UTF-8",
            "-o",
            str(ui_pot),
            *[str(p) for p in sorted(src.rglob("*.ui"))],
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    count = len({e.msgid for e in polib.pofile(str(ui_pot)) if e.msgid})
    assert count >= _UI_MSGID_FLOOR, f"only {count} msgids from the .ui files"


def test_vendored_its_rules_exist() -> None:
    """The ITS rules the generator needs are vendored, not looked up."""
    assert _VENDORED_ITS.is_file(), f"{_VENDORED_ITS} is missing"
    loc = _VENDORED_ITS.with_suffix(".loc")
    assert loc.is_file(), f"{loc} is missing"


def _run_its_drift(tmp_path: Path, its_dir: Path) -> subprocess.CompletedProcess[str]:
    """Run check_po.py over a stub catalog, pointing the ITS check at a dir."""
    src = tmp_path / "po"
    src.mkdir()
    (src / "scantpaper-de.po").write_text(
        'msgid ""\n'
        'msgstr ""\n'
        '"MIME-Version: 1.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        '"Language: de\\n"\n'
        f'"Plural-Forms: {_PLURAL_FORMS["de"]}\\n"\n',
        encoding="utf-8",
    )
    empty_pot = tmp_path / "empty.pot"
    empty_pot.write_text(
        'msgid ""\nmsgstr ""\n"MIME-Version: 1.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n',
        encoding="utf-8",
    )
    return subprocess.run(
        [
            "python3",
            str(REPO_ROOT / "dev" / "check_po.py"),
            "--src",
            str(src),
            "--pot",
            str(empty_pot),
            "--its-dir",
            str(its_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_its_rules_matching_the_system_are_reported_as_matching(
    tmp_path: Path,
) -> None:
    """An installed copy identical to the vendored one is reported as such."""
    its_dir = tmp_path / "its"
    its_dir.mkdir()
    for name in ("gtkbuilder.its", "gtkbuilder.loc"):
        (its_dir / name).write_bytes(
            (REPO_ROOT / "dev" / name).read_bytes(),
        )
    result = _run_its_drift(tmp_path, its_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "matches" in result.stdout
    assert "differs" not in result.stdout
    assert "no installed copy" not in result.stdout


def test_its_rules_differing_from_the_system_are_reported(tmp_path: Path) -> None:
    """An installed copy that differs is reported, naming both files."""
    its_dir = tmp_path / "its"
    its_dir.mkdir()
    (its_dir / "gtkbuilder.its").write_text(
        "<!-- a different upstream revision -->\n", encoding="utf-8"
    )
    (its_dir / "gtkbuilder.loc").write_bytes(
        (REPO_ROOT / "dev" / "gtkbuilder.loc").read_bytes(),
    )
    result = _run_its_drift(tmp_path, its_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "differs" in result.stdout
    assert str(its_dir / "gtkbuilder.its") in result.stdout
    assert str(_VENDORED_ITS) in result.stdout


def test_absent_system_its_rules_are_distinguishable_from_a_match(
    tmp_path: Path,
) -> None:
    """No installed copy is reported as its own case, not as a match."""
    its_dir = tmp_path / "its"
    its_dir.mkdir()
    result = _run_its_drift(tmp_path, its_dir)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "no installed copy" in result.stdout
    assert "matches" not in result.stdout


def test_generate_pot_leaves_the_ui_sources_in_place(tmp_path: Path) -> None:
    """Generation removes only its own temporaries, never the .ui sources.

    The generator runs with the source directory as its working directory, so
    a stray entry in its cleanup list would silently delete a tracked source
    file rather than a temporary.
    """
    src = REPO_ROOT / "src" / "scantpaper"
    ui_files = sorted(src.rglob("*.ui"))
    assert ui_files, "no .ui sources found to check against"

    before = {p: p.read_bytes() for p in ui_files}
    result = _run_generate_pot(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr

    missing = [p for p in ui_files if not p.is_file()]
    assert not missing, f"generation deleted {[p.name for p in missing]}"
    for path, content in before.items():
        assert path.read_bytes() == content, f"generation altered {path.name}"
    assert not list(src.glob("_*_tmp.pot")), "temporary pots were left behind"
    assert not list(src.glob("*.ui.h")), "intermediate headers were left behind"
