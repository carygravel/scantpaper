"""Declarative registry of the external programs scantpaper depends on.

Each dependency is a ``Dependency`` record that is the single source of
truth for how it is detected (a pure probe returning a version or ``None``),
whether it is warned about at startup, and the user-facing message used in
that warning. ``_check_dependencies`` and ``_missing_packages_message`` are
both derived from this registry so detection and messaging cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

import tesserocr

from scantpaper import config
from scantpaper.helpers import program_version
from scantpaper.i18n import _

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class ProbeResult:
    """Result of probing a dependency.

    ``version`` is the installed program's version, or ``None`` when it is
    absent. ``using_fallback`` is set when the version was obtained by
    falling back to a compatible program (e.g. GraphicsMagick standing in
    for ImageMagick).
    """

    version: str | None
    using_fallback: bool = False


@dataclass(frozen=True)
class Dependency:
    """One external program the application can detect and warn about."""

    name: str
    probe: Callable[[], ProbeResult]
    message: str = ""
    warn_at_startup: bool = False


def program_version_probe(
    stream: str, regex: str, cmd: list[str]
) -> Callable[[], ProbeResult]:
    """Return a probe that parses a version from ``cmd``'s output stream."""

    def probe() -> ProbeResult:
        return ProbeResult(program_version(stream, regex, cmd))

    return probe


@lru_cache
def _graphicsmagick_version() -> str | None:
    """Return the GraphicsMagick version, probing it at most once."""
    return program_version("stdout", r"GraphicsMagick\s([\d.-]+)", ["gm", "-version"])


def probe_imagemagick() -> ProbeResult:
    """Probe ImageMagick, falling back to GraphicsMagick compatibility mode."""
    version = program_version(
        "stdout",
        r"Version:\sImageMagick\s([\d.-]+)",
        [config.CONVERT_COMMAND, "--version"],
    )
    if bool(version):
        return ProbeResult(version)
    gm = _graphicsmagick_version()
    if bool(gm):
        return ProbeResult(gm, using_fallback=True)
    return ProbeResult(None)


def probe_graphicsmagick() -> ProbeResult:
    """Probe GraphicsMagick."""
    return ProbeResult(_graphicsmagick_version())


def probe_unpaper() -> ProbeResult:
    """Probe unpaper."""
    return ProbeResult(program_version("stdout", r"([\d.]+)", ["unpaper", "--version"]))


@lru_cache
def _jbig2_version() -> str | None:
    """Return the jbig2enc version, probing it at most once."""
    return program_version("stderr", r"jbig2enc\s+([\d.]+)", ["jbig2", "--version"])


def probe_jbig2() -> ProbeResult:
    """Probe the JBIG2 encoder."""
    return ProbeResult(_jbig2_version())


def jbig2_available() -> bool:
    """Return True when the JBIG2 encoder (``jbig2``) is installed."""
    return _jbig2_version() is not None


def probe_tesseract() -> ProbeResult:
    """Probe the tesseract version reported by the tesserocr binding."""
    return ProbeResult(tesserocr.tesseract_version())


def probe_tesserocr() -> ProbeResult:
    """Probe the tesserocr binding version."""
    return ProbeResult(tesserocr.__version__)


# Ordered so that the startup missing-package warning reads
# imagemagick, libtiff, djvu, xdg, unpaper, tesseract, qpdf, jbig2.
DEPS = (
    Dependency(
        "imagemagick",
        probe_imagemagick,
        _("Save image and Save as PDF both require imagemagick"),
        warn_at_startup=True,
    ),
    Dependency(
        "libtiff",
        program_version_probe("both", r"LIBTIFF,\sVersion\s([\d.]+)", ["tiffcp", "-h"]),
        _("Save image requires libtiff"),
        warn_at_startup=True,
    ),
    Dependency(
        "djvu",
        program_version_probe("stderr", r"DjVuLibre-([\d.]+)", ["cjb2", "--version"]),
        _("Save as DjVu requires djvulibre-bin"),
        warn_at_startup=True,
    ),
    Dependency(
        "xdg",
        program_version_probe(
            "stdout", r"xdg-email\s([^\n]+)", ["xdg-email", "--version"]
        ),
        _("Email as PDF requires xdg-email"),
        warn_at_startup=True,
    ),
    Dependency("unpaper", probe_unpaper, _("unpaper missing"), warn_at_startup=True),
    Dependency(
        "tesseract", probe_tesseract, _("OCR requires tesseract"), warn_at_startup=True
    ),
    Dependency(
        "qpdf",
        program_version_probe("stdout", r"([\d.]+)", ["qpdf", "--version"]),
        _("PDF encryption requires qpdf"),
        warn_at_startup=True,
    ),
    Dependency(
        "jbig2",
        probe_jbig2,
        _("JBIG2 PDF compression requires jbig2"),
        warn_at_startup=True,
    ),
    Dependency("graphicsmagick", probe_graphicsmagick),
    Dependency(
        "pdftops",
        program_version_probe(
            "stderr", r"pdftops\sversion\s([\d.]+)", ["pdftops", "-v"]
        ),
    ),
    Dependency(
        "pdfunite",
        program_version_probe(
            "stderr", r"pdfunite\sversion\s([\d.]+)", ["pdfunite", "-v"]
        ),
    ),
    Dependency(
        "pdf2ps", program_version_probe("stdout", r"([\d.]+)", ["gs", "--version"])
    ),
    Dependency("tesserocr", probe_tesserocr),
)
