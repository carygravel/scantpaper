"""Test tesseract helper functions."""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from scantpaper import config
from scantpaper.document import Document
from scantpaper.helpers import Proc
from scantpaper.loop_helpers import safe_mainloop
from scantpaper.tesseract import (
    _iso639_1to3,
    find_system_tessdata_dir,
    get_tesseract_codes,
    get_tesseract_variables,
    join_language_spec,
    languages,
    locale_installed,
    parse_variables,
    resolve_file_variables,
    resolve_tessdata_dir,
    split_language_spec,
    validate_file_variables,
    validate_language_spec,
    validate_tessdata_dir,
    validate_variable_names,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def _select_multiple_languages(codes: list[str]) -> str:
    """Pick a primary and an additional language for a multi-language test."""
    languages = [code for code in codes if code not in {"osd", "equ"}]
    if len(languages) < 2:
        pytest.skip("requires two installed OCR languages")
    if "eng" in languages:
        languages.remove("eng")
        return "+".join(["eng", languages[0]])
    return "+".join(languages[:2])


def test_select_multiple_languages_eng_first() -> None:
    """English is chosen as the primary when it is installed."""
    assert _select_multiple_languages(["deu", "eng", "fra"]) == "eng+deu"


def test_select_multiple_languages_no_eng() -> None:
    """The first two installed languages are used when English is absent."""
    assert _select_multiple_languages(["deu", "fra"]) == "deu+fra"


def test_select_multiple_languages_filters_osd_equ() -> None:
    """Osd and equ are not treated as OCR languages."""
    assert _select_multiple_languages(["osd", "eng", "equ", "deu"]) == "eng+deu"


def test_select_multiple_languages_too_few_skips() -> None:
    """A single installed language skips the multi-language test."""
    with pytest.raises(pytest.skip.Exception):
        _select_multiple_languages(["eng"])


def test_tesseract_code_conversions() -> None:
    """Test tesseract helper functions."""
    assert languages(["eng", "deu", "chi-sim-vert"]) == {
        "chi-sim-vert": "Chinese - Simplified (vertical)",
        "eng": "English",
        "deu": "German",
    }, "test languages()"
    assert _iso639_1to3("en") == "eng", "_iso639_1to3 en"
    assert _iso639_1to3("C") == "eng", "_iso639_1to3 C"
    assert _iso639_1to3("c") == "eng", "_iso639_1to3 c (lowercase)"
    assert _iso639_1to3("zh") == "chi-sim", "_iso639_1to3 zh"
    assert locale_installed("en_GB", ["eng"]) == "", "language installed"
    assert re.search(r"install", locale_installed("de_DE", ["eng"])), (
        "language installable"
    )
    assert re.search(r"developers", locale_installed("kw_KW", ["eng"])), (
        "language not installable"
    )
    assert re.search(r"necessary", locale_installed("zz_ZZ", ["eng"])), (
        "language unknown"
    )
    # Test C.UTF-8 locale - should map to en_US like C does
    assert locale_installed("C.UTF-8", ["eng"]) == "", (
        "C.UTF-8 locale should map to eng"
    )
    # Test uppercase C locale still works
    assert locale_installed("C", ["eng"]) == "", "C locale should map to eng"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_get_tesseract_codes() -> None:
    """Test get_tesseract_codes()."""
    assert isinstance(get_tesseract_codes(), list), "get_tesseract_codes() returns list"


def test_get_tesseract_codes_mocked(mocker: pytest.MockerFixture) -> None:
    """Test get_tesseract_codes() with mocked exec_command."""
    mock_exec = mocker.patch("scantpaper.tesseract.exec_command")

    # Case 1: stdout is None (tesseract not found)
    mock_exec.return_value = Proc(-1, None, "not found")
    assert get_tesseract_codes() == []

    # Case 2: stdout with header and trailing newline
    mock_exec.return_value = Proc(
        0, "List of available languages (3):\neng\ndeu\nosd\n", ""
    )
    assert get_tesseract_codes() == ["eng", "deu", "osd"]

    # Case 3: stdout without header, without trailing newline
    mock_exec.return_value = Proc(0, "eng\ndeu", "")
    assert get_tesseract_codes() == ["eng", "deu"]


def test_split_language_spec() -> None:
    """Test splitting language specifications."""
    assert split_language_spec(None) == []
    assert split_language_spec("") == []
    assert split_language_spec("eng") == ["eng"]
    assert split_language_spec("deu+eng") == ["deu", "eng"]
    assert split_language_spec(" deu + eng + ") == ["deu", "eng"]
    assert split_language_spec("eng++fra") == ["eng", "fra"]
    assert split_language_spec("deu+deu+eng") == ["deu", "eng"]


def test_join_language_spec() -> None:
    """Test joining language specifications."""
    assert join_language_spec(None) == ""
    assert join_language_spec("eng") == "eng"
    assert join_language_spec("deu", ["eng"]) == "deu+eng"
    assert join_language_spec("deu", ["eng", "fra"]) == "deu+eng+fra"
    assert join_language_spec(" deu ", [" eng ", ""]) == "deu+eng"
    assert join_language_spec("deu", ["deu", "eng"]) == "deu+eng"
    assert join_language_spec(None, ["eng", "deu"]) == "eng+deu"
    assert join_language_spec("deu", split_language_spec("deu+eng")) == "deu+eng"


def test_parse_variables() -> None:
    """Test parsing tesseract variables."""
    assert parse_variables(None) == {}
    assert parse_variables("") == {}
    assert parse_variables("user_words_file=/tmp/words.txt") == {
        "user_words_file": "/tmp/words.txt"
    }
    assert parse_variables(
        "\n# comment\n user_words_file = /tmp/words.txt \n\n"
        " tessedit_char_whitelist = 0123 \n"
    ) == {
        "user_words_file": "/tmp/words.txt",
        "tessedit_char_whitelist": "0123",
    }
    assert parse_variables("some_variable=a=b") == {"some_variable": "a=b"}
    assert parse_variables("x=1\nx=2") == {"x": "2"}
    assert parse_variables("-c tessedit_char_whitelist=0123") == {
        "tessedit_char_whitelist": "0123"
    }
    with pytest.raises(ValueError, match="line 2"):
        parse_variables("good=1\nbad")
    with pytest.raises(ValueError, match="line 1"):
        parse_variables("=value")
    with pytest.raises(ValueError, match="line 1"):
        parse_variables("-c bad")


def test_parse_variables_command_line_flags() -> None:
    """Test that command-line options are rejected with the parameter to use."""
    with pytest.raises(ValueError, match="--user-words") as excinfo:
        parse_variables("--user-words /tmp/words.txt")
    assert "user_words_file" in str(excinfo.value)
    assert "/tmp/words.txt" in str(excinfo.value)

    with pytest.raises(ValueError, match="--user-patterns") as excinfo:
        parse_variables("--user-patterns /tmp/patterns")
    assert "user_patterns_file" in str(excinfo.value)

    with pytest.raises(ValueError, match="--dpi") as excinfo:
        parse_variables("--dpi 300")
    assert "user_defined_dpi" in str(excinfo.value)

    with pytest.raises(ValueError, match="--psm") as excinfo:
        parse_variables("--psm 6")
    assert "user_defined_dpi" not in str(excinfo.value)


def test_validate_file_variables(tmp_path: pathlib.Path) -> None:
    """Test checking file-valued engine parameters."""
    assert validate_file_variables({}) is None

    missing = tmp_path / "missing.txt"
    error = validate_file_variables({"user_words_file": str(missing)})
    assert error is not None
    assert "user_words_file" in error
    assert str(missing) in error

    words = tmp_path / "words.txt"
    words.write_text("fox\n")
    assert validate_file_variables({"user_words_file": str(words)}) is None

    # A tilde is not expanded, so a path under the home directory is used
    # literally and reported as resolved.
    error = validate_file_variables({"user_words_file": "~/words.txt"})
    assert error is not None
    assert "~" in error


def test_validate_file_variables_unreadable(
    tmp_path: pathlib.Path, mocker: pytest.MockerFixture
) -> None:
    """Test that an unreadable word list is reported."""
    words = tmp_path / "words.txt"
    words.write_text("fox\n")
    mocker.patch("scantpaper.tesseract.os.access", return_value=False)
    error = validate_file_variables({"user_patterns_file": str(words)})
    assert error is not None
    assert "user_patterns_file" in error
    assert str(words) in error


def test_resolve_file_variables() -> None:
    """Test that file-valued parameters are resolved and others are left alone."""
    resolved = resolve_file_variables(
        {"user_words_file": "words.txt", "tessedit_char_whitelist": "0123"}
    )
    assert resolved["user_words_file"] == str(pathlib.Path("words.txt").resolve())
    assert resolved["tessedit_char_whitelist"] == "0123"


def test_validate_language_spec() -> None:
    """Test finding languages that are not installed."""
    assert validate_language_spec("eng", ["eng", "deu"]) == []
    assert validate_language_spec("deu+eng", ["eng"]) == ["deu"]
    assert validate_language_spec("deu+deu", ["eng"]) == ["deu"]
    assert validate_language_spec(None, ["eng"]) == []


def test_validate_variable_names() -> None:
    """Test finding unknown tesseract variables."""
    known = {"user_words_file", "tessedit_char_whitelist"}
    assert validate_variable_names({"user_words_file": "x"}, known) == []
    assert validate_variable_names({"bad": "x", "user_words_file": "x"}, known) == [
        "bad"
    ]
    assert validate_variable_names({"bad": "x"}, None) == []


def test_get_tesseract_variables(mocker: pytest.MockerFixture) -> None:
    """Test querying the tesseract variable names."""
    get_tesseract_variables.cache_clear()
    mock_exec = mocker.patch("scantpaper.tesseract.exec_command")
    mock_exec.return_value = Proc(
        0,
        "Tesseract parameters:\n"
        "user_words_file\tSTRING\tUser words file\n"
        "preserve_interword_spaces\tINT\t0\n",
        "",
    )
    assert get_tesseract_variables() == {
        "user_words_file",
        "preserve_interword_spaces",
    }
    # Cached: the command is only called once.
    assert get_tesseract_variables() == {
        "user_words_file",
        "preserve_interword_spaces",
    }
    mock_exec.assert_called_once()

    get_tesseract_variables.cache_clear()
    mock_exec.return_value = Proc(-1, None, "not found")
    assert get_tesseract_variables() is None

    get_tesseract_variables.cache_clear()
    mock_exec.return_value = Proc(0, "Tesseract parameters:\n", "")
    assert get_tesseract_variables() is None

    get_tesseract_variables.cache_clear()
    mock_exec.return_value = Proc(0, "unexpected output\n", "")
    assert get_tesseract_variables() is None


def test_tesseract_in_thread(
    temp_png: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test importing PDF."""
    args = [
        config.CONVERT_COMMAND,
        "-density",
        "300",
        "label:The quick brown fox",
        "-alpha",
        "Off",
        "-depth",
        "1",
        "-colorspace",
        "Gray",
        "-family",
        "DejaVu Sans",
        "-pointsize",
        "12",
        temp_png.name,
    ]
    subprocess.run(args, check=True)

    slist = Document(db=temp_db.name)

    import_in_mainloop(slist, [temp_png.name])

    image_id_before = get_page_sync(slist.thread, id=1).image_id

    mlp = safe_mainloop(10000)
    slist.tesseract(
        page=slist.data[0][2],
        language="eng",
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    assert page.image_id == image_id_before, "OCR does not change the stored image"
    hocr = page.export_hocr()
    assert re.search(r"T[hn]e", hocr), 'Tesseract returned "The"'
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'
    assert re.search(r"brown", hocr), 'Tesseract returned "brown"'
    assert re.search(r"f(o|0)x", hocr), 'Tesseract returned "fox"'


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="requires tesseract")
def test_tesseract_with_multiple_languages(
    temp_png: object,
    temp_db: object,
    import_in_mainloop: Callable[[object, list[str]], None],
    get_page_sync: Callable[..., object],
) -> None:
    """Test OCR with an ordered multi-language specification."""
    language = _select_multiple_languages(get_tesseract_codes())

    args = [
        config.CONVERT_COMMAND,
        "-density",
        "300",
        "label:The quick brown fox",
        "-alpha",
        "Off",
        "-depth",
        "1",
        "-colorspace",
        "Gray",
        "-family",
        "DejaVu Sans",
        "-pointsize",
        "12",
        temp_png.name,
    ]
    subprocess.run(args, check=True)

    slist = Document(db=temp_db.name)
    import_in_mainloop(slist, [temp_png.name])

    mlp = safe_mainloop(10000)
    slist.tesseract(
        page=slist.data[0][2],
        language=language,
        finished_callback=lambda _response: mlp.quit(),
    )
    mlp.run()

    page = get_page_sync(slist.thread, id=1)
    hocr = page.export_hocr()
    assert re.search(r"quick", hocr), 'Tesseract returned "quick"'


def _make_tessdata(path: pathlib.Path) -> pathlib.Path:
    """Create a directory that looks like a tessdata directory."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "eng.traineddata").write_bytes(b"")
    return path


def test_validate_tessdata_dir_accepts_direct_traineddata(
    tmp_path: pathlib.Path,
) -> None:
    """A directory directly containing traineddata is valid."""
    _make_tessdata(tmp_path)
    assert validate_tessdata_dir(str(tmp_path)) is None


def test_validate_tessdata_dir_rejects_missing(tmp_path: pathlib.Path) -> None:
    """A missing directory is reported."""
    error = validate_tessdata_dir(str(tmp_path / "missing"))
    assert error is not None
    assert "does not exist" in error
    assert "missing" in error


def test_validate_tessdata_dir_rejects_file(tmp_path: pathlib.Path) -> None:
    """A file is not a tessdata directory."""
    path = tmp_path / "eng.traineddata"
    path.write_bytes(b"")
    error = validate_tessdata_dir(str(path))
    assert error is not None
    assert "not a directory" in error


def test_validate_tessdata_dir_rejects_unreadable(tmp_path: pathlib.Path) -> None:
    """An unreadable directory is reported."""
    path = tmp_path / "unreadable"
    path.mkdir()
    path.chmod(0)
    try:
        error = validate_tessdata_dir(str(path))
    finally:
        path.chmod(0o755)
    assert error is not None
    assert "cannot be read" in error


def test_validate_tessdata_dir_rejects_nested_data(tmp_path: pathlib.Path) -> None:
    """Only traineddata directly in the directory counts."""
    _make_tessdata(tmp_path / "tessdata")
    error = validate_tessdata_dir(str(tmp_path))
    assert error is not None
    assert "No Tesseract language data" in error
    assert str((tmp_path / "tessdata").resolve()) + "/" in error


def test_find_system_tessdata_dir_from_glob(mocker: pytest.MockerFixture) -> None:
    """The distribution layout is found with a glob."""
    mock_glob = mocker.patch.object(
        pathlib.Path,
        "glob",
        return_value=["/usr/share/tesseract-ocr/4.00/tessdata"],
    )
    assert find_system_tessdata_dir() == "/usr/share/tesseract-ocr/4.00/tessdata"
    mock_glob.assert_called_with("*/tessdata")


def test_find_system_tessdata_dir_flat_layout(mocker: pytest.MockerFixture) -> None:
    """The SUSE flat layout is found when no versioned directory exists."""
    mocker.patch.object(pathlib.Path, "glob", return_value=[])
    mocker.patch.object(
        pathlib.Path,
        "is_dir",
        autospec=True,
        side_effect=lambda self: (
            self == pathlib.Path("/usr/share/tesseract-ocr/tessdata")
        ),
    )
    assert find_system_tessdata_dir() == "/usr/share/tesseract-ocr/tessdata"


def test_find_system_tessdata_dir_none(mocker: pytest.MockerFixture) -> None:
    """No guess is returned when no layout matches."""
    mocker.patch.object(pathlib.Path, "glob", return_value=[])
    mocker.patch.object(pathlib.Path, "is_dir", return_value=False)
    mocker.patch("scantpaper.tesseract.shutil.which", return_value=None)
    assert find_system_tessdata_dir() is None


def test_resolve_tessdata_dir_explicit_wins(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit selection wins over TESSDATA_PREFIX."""
    explicit = _make_tessdata(tmp_path / "best")
    environment = _make_tessdata(tmp_path / "system")
    monkeypatch.setenv("TESSDATA_PREFIX", str(environment))
    path, error = resolve_tessdata_dir(str(explicit))
    assert error is None
    assert path == str(explicit.resolve()) + "/"


def test_resolve_tessdata_dir_uses_environment(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TESSDATA_PREFIX is used when nothing is selected."""
    environment = _make_tessdata(tmp_path / "system")
    monkeypatch.setenv("TESSDATA_PREFIX", str(environment))
    path, error = resolve_tessdata_dir("")
    assert error is None
    assert path == str(environment.resolve()) + "/"


def test_resolve_tessdata_dir_uses_system_default(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """The system default is used without a selection or environment."""
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    system = _make_tessdata(tmp_path / "system")
    mocker.patch(
        "scantpaper.tesseract.tesserocr.get_languages",
        return_value=(str(system), ["eng"]),
    )
    path, error = resolve_tessdata_dir("")
    assert error is None
    assert path == str(system.resolve()) + "/"


def test_resolve_tessdata_dir_does_not_fall_back(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid explicit selection is not replaced by the environment."""
    environment = _make_tessdata(tmp_path / "system")
    monkeypatch.setenv("TESSDATA_PREFIX", str(environment))
    path, error = resolve_tessdata_dir(str(tmp_path / "missing"))
    assert path is None
    assert error is not None
    assert "does not exist" in error


def test_resolve_tessdata_dir_rejects_broad_environment(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """A broad TESSDATA_PREFIX is rejected without asking tesseract."""
    _make_tessdata(tmp_path / "tessdata")
    monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    mock_languages = mocker.patch("scantpaper.tesseract.tesserocr.get_languages")
    path, error = resolve_tessdata_dir("")
    assert path is None
    assert error is not None
    assert "No Tesseract language data" in error
    mock_languages.assert_not_called()


def test_resolve_tessdata_dir_falls_back_from_dot_slash(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """The distribution fallback is used when tesseract reports ./."""
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    system = _make_tessdata(tmp_path / "system")
    mocker.patch(
        "scantpaper.tesseract.tesserocr.get_languages",
        return_value=("./", []),
    )
    mocker.patch(
        "scantpaper.tesseract.find_system_tessdata_dir",
        return_value=str(system),
    )
    path, error = resolve_tessdata_dir("")
    assert error is None
    assert path == str(system.resolve()) + "/"


def test_get_tesseract_codes_uses_tessdata_dir(
    mocker: pytest.MockerFixture,
) -> None:
    """A known directory is passed to tesseract."""
    mock_exec = mocker.patch("scantpaper.tesseract.exec_command")
    mock_exec.return_value = Proc(0, "eng\ndeu\n", "")
    assert get_tesseract_codes("/models/tessdata/") == ["eng", "deu"]
    mock_exec.assert_called_once_with(
        ["tesseract", "--list-langs", "--tessdata-dir", "/models/tessdata/"]
    )


def test_get_tesseract_codes_guards_broad_environment(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """A broad TESSDATA_PREFIX is rejected before tesseract runs."""
    _make_tessdata(tmp_path / "tessdata")
    monkeypatch.setenv("TESSDATA_PREFIX", str(tmp_path))
    mock_exec = mocker.patch("scantpaper.tesseract.exec_command")
    assert get_tesseract_codes() == []
    mock_exec.assert_not_called()


def test_get_tesseract_codes_uses_valid_environment(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """A valid TESSDATA_PREFIX is passed to tesseract."""
    environment = _make_tessdata(tmp_path / "system")
    monkeypatch.setenv("TESSDATA_PREFIX", str(environment))
    mock_exec = mocker.patch("scantpaper.tesseract.exec_command")
    mock_exec.return_value = Proc(0, "eng\n", "")
    assert get_tesseract_codes() == ["eng"]
    mock_exec.assert_called_once_with(
        [
            "tesseract",
            "--list-langs",
            "--tessdata-dir",
            str(environment.resolve()) + "/",
        ]
    )


def test_validate_tessdata_dir_without_suggestion(tmp_path: pathlib.Path) -> None:
    """An empty directory with no tessdata child reports no suggestion."""
    error = validate_tessdata_dir(str(tmp_path))
    assert error is not None
    assert "No Tesseract language data" in error
    assert "Did you mean" not in error


def test_validate_tessdata_dir_handles_unreadable_listing(
    tmp_path: pathlib.Path, mocker: pytest.MockerFixture
) -> None:
    """A directory whose listing fails is reported as unreadable."""
    mocker.patch("scantpaper.tesseract.os.access", return_value=True)
    mocker.patch.object(pathlib.Path, "iterdir", side_effect=OSError("denied"))
    error = validate_tessdata_dir(str(tmp_path))
    assert error is not None
    assert "No Tesseract language data" in error


def test_resolve_tessdata_dir_default_not_found(
    monkeypatch: pytest.MonkeyPatch, mocker: pytest.MockerFixture
) -> None:
    """Tesseract reporting ./ with no guess is an error."""
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    mocker.patch(
        "scantpaper.tesseract.tesserocr.get_languages",
        return_value=("./", []),
    )
    mocker.patch("scantpaper.tesseract.find_system_tessdata_dir", return_value=None)
    path, error = resolve_tessdata_dir("")
    assert path is None
    assert error is not None
    assert "not found" in error


def test_resolve_tessdata_dir_validates_system_default(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: pytest.MockerFixture,
) -> None:
    """An invalid system default is reported rather than used."""
    monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
    mocker.patch(
        "scantpaper.tesseract.tesserocr.get_languages",
        return_value=(str(tmp_path), []),
    )
    path, error = resolve_tessdata_dir("")
    assert path is None
    assert error is not None
    assert "No Tesseract language data" in error


def test_find_system_tessdata_dir_symlink(
    tmp_path: pathlib.Path, mocker: pytest.MockerFixture
) -> None:
    """The homebrew-style symlink layout is found."""
    real = tmp_path / "real"
    (real / "bin").mkdir(parents=True)
    (real / "share" / "tessdata").mkdir(parents=True)
    exe = real / "bin" / "tesseract"
    exe.write_text("")
    link = tmp_path / "tesseract-link"
    link.symlink_to(exe)

    mocker.patch.object(pathlib.Path, "glob", return_value=[])
    mocker.patch.object(pathlib.Path, "is_dir", return_value=False)
    mocker.patch("scantpaper.tesseract.shutil.which", return_value=str(link))

    assert find_system_tessdata_dir() == str(real / "share" / "tessdata")
