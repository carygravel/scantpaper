"""Unit tests for the declarative dependency registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scantpaper.dependencies import (
    DEPS,
    ProbeResult,
    _ghostscript_rewrites_bilevel_to_flate,
    _ghostscript_version,
    ghostscript_version,
    jbig2_available,
    probe_ghostscript,
    program_version_probe,
)

if TYPE_CHECKING:
    import pytest


def _deps_by_name() -> dict[str, object]:
    return {dep.name: dep for dep in DEPS}


def test_program_version_probe_parses_version(mocker: pytest.MockerFixture) -> None:
    """A command probe parses the version from the program output."""
    mock = mocker.patch("scantpaper.dependencies.program_version", return_value="1.2.3")
    probe = program_version_probe("stdout", r"v([\d.]+)", ["tool", "--version"])
    result = probe()
    assert result == ProbeResult("1.2.3")
    mock.assert_called_once_with("stdout", r"v([\d.]+)", ["tool", "--version"])


def test_program_version_probe_absent_returns_none(
    mocker: pytest.MockerFixture,
) -> None:
    """A command probe reports None when the program is absent."""
    mocker.patch("scantpaper.dependencies.program_version", return_value=None)
    result = program_version_probe("stdout", r"v([\d.]+)", ["tool", "--version"])()
    assert result == ProbeResult(None)


def test_probe_imagemagick_present(mocker: pytest.MockerFixture) -> None:
    """ImageMagick is reported without the fallback flag when present."""
    mock = mocker.patch(
        "scantpaper.dependencies.program_version", return_value="6.9.11-60"
    )
    result = _deps_by_name()["imagemagick"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("6.9.11-60")
    mock.assert_called_once()


def test_probe_imagemagick_graphicsmagick_fallback(
    mocker: pytest.MockerFixture,
) -> None:
    """Missing ImageMagick falls back to GraphicsMagick and flags it."""
    mocker.patch("scantpaper.dependencies.program_version", return_value=None)
    mocker.patch(
        "scantpaper.dependencies._graphicsmagick_version", return_value="1.3.41"
    )
    result = _deps_by_name()["imagemagick"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("1.3.41", using_fallback=True)


def test_probe_imagemagick_absent(mocker: pytest.MockerFixture) -> None:
    """Both missing yields a None version and no fallback."""
    mocker.patch("scantpaper.dependencies.program_version", return_value=None)
    mocker.patch("scantpaper.dependencies._graphicsmagick_version", return_value=None)
    result = _deps_by_name()["imagemagick"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult(None)


def test_probe_graphicsmagick(mocker: pytest.MockerFixture) -> None:
    """GraphicsMagick reports its cached version."""
    mocker.patch(
        "scantpaper.dependencies._graphicsmagick_version", return_value="1.3.41"
    )
    result = _deps_by_name()["graphicsmagick"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("1.3.41")


def test_probe_unpaper(mocker: pytest.MockerFixture) -> None:
    """Unpaper reports its version."""
    mocker.patch("scantpaper.dependencies.program_version", return_value="1.0.35")
    result = _deps_by_name()["unpaper"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("1.0.35")


def test_probe_tesseract(mocker: pytest.MockerFixture) -> None:
    """Tesseract reports the tesserocr binding version."""
    mocker.patch("tesserocr.tesseract_version", return_value="4.1.1")
    result = _deps_by_name()["tesseract"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("4.1.1")


def test_probe_tesserocr(mocker: pytest.MockerFixture) -> None:
    """Tesserocr reports its own version."""
    mocker.patch("tesserocr.__version__", "2.5")
    result = _deps_by_name()["tesserocr"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("2.5")


def test_probe_jbig2(mocker: pytest.MockerFixture) -> None:
    """The JBIG2 encoder reports its version."""
    mocker.patch("scantpaper.dependencies._jbig2_version", return_value="0.32")
    result = _deps_by_name()["jbig2"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult("0.32")


def test_probe_jbig2_absent(mocker: pytest.MockerFixture) -> None:
    """A missing JBIG2 encoder yields a None version."""
    mocker.patch("scantpaper.dependencies._jbig2_version", return_value=None)
    result = _deps_by_name()["jbig2"].probe()  # type: ignore[attr-defined]
    assert result == ProbeResult(None)


def test_jbig2_available_delegates_to_probe(
    mocker: pytest.MockerFixture,
) -> None:
    """jbig2_available reflects the cached probe's result."""
    mocker.patch("scantpaper.dependencies._jbig2_version", return_value="0.32")
    assert jbig2_available() is True
    mocker.patch("scantpaper.dependencies._jbig2_version", return_value=None)
    assert jbig2_available() is False


def test_probe_ghostscript(mocker: pytest.MockerFixture) -> None:
    """Ghostscript reports the version parsed from its output."""
    mocker.patch("scantpaper.dependencies._ghostscript_version", return_value="10.06.0")
    assert probe_ghostscript() == ProbeResult("10.06.0")


def test_ghostscript_version_reads_program_version(
    mocker: pytest.MockerFixture,
) -> None:
    """The cached probe parses the installed Ghostscript version."""
    mocker.patch("scantpaper.dependencies.program_version", return_value="10.06.0")
    _ghostscript_version.cache_clear()
    try:
        assert ghostscript_version() == "10.06.0"
    finally:
        _ghostscript_version.cache_clear()


def test_ghostscript_version_delegates_to_probe(
    mocker: pytest.MockerFixture,
) -> None:
    """ghostscript_version returns the cached probe's result."""
    mocker.patch("scantpaper.dependencies._ghostscript_version", return_value="9.55.0")
    assert ghostscript_version() == "9.55.0"
    mocker.patch("scantpaper.dependencies._ghostscript_version", return_value=None)
    assert ghostscript_version() is None


def test_ghostscript_rewrites_bilevel_to_flate() -> None:
    """Only Ghostscript 10.06 and later rewrite bilevel images as Flate."""
    assert _ghostscript_rewrites_bilevel_to_flate("10.06.0") is True
    assert _ghostscript_rewrites_bilevel_to_flate("10.07.1") is True
    assert _ghostscript_rewrites_bilevel_to_flate("10.02.1") is False
    assert _ghostscript_rewrites_bilevel_to_flate("9.55.0") is False
    assert _ghostscript_rewrites_bilevel_to_flate(None) is False
    assert _ghostscript_rewrites_bilevel_to_flate("garbage") is False


def test_deps_names_are_unique() -> None:
    """Every dependency has a distinct name so the dict has no collisions."""
    names = [dep.name for dep in DEPS]
    assert len(names) == len(set(names))


def test_deps_startup_order_and_messages() -> None:
    """Startup-warned deps appear in message order with a message each."""
    warned = [(dep.name, dep.message) for dep in DEPS if dep.warn_at_startup]
    assert [name for name, _message in warned] == [
        "imagemagick",
        "libtiff",
        "djvu",
        "xdg",
        "unpaper",
        "tesseract",
        "qpdf",
        "jbig2",
    ]
    assert all(message for _name, message in warned), "every warned dep has a message"
