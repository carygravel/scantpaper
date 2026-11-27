"""Tests for the shared test-environment probes and markers."""

from __future__ import annotations

import locale
import shutil
from typing import TYPE_CHECKING

from scantpaper.tests import environment

if TYPE_CHECKING:
    import pytest


def test_de_locale_constant() -> None:
    """The shared locale name is the German comma locale."""
    assert environment.DE_LOCALE == "de_DE.utf8"


def test_has_locale_available() -> None:
    """The portable C locale is always available."""
    assert environment.has_locale("C") is True


def test_has_locale_missing() -> None:
    """An unknown locale is reported as unavailable."""
    assert environment.has_locale("no.such.locale.zzz") is False


def test_has_locale_category() -> None:
    """The category argument is forwarded to setlocale."""
    assert environment.has_locale("C", locale.LC_CTYPE) is True


def test_requires_locale_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is true when the probe is false."""
    monkeypatch.setattr(environment, "has_locale", lambda _name, _category=None: False)
    marker = environment.requires_locale("xx_XX.utf8")
    assert marker.mark.args[0] is True
    assert marker.mark.kwargs["reason"] == "xx_XX.utf8 locale not available"


def test_requires_locale_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is false when the probe is true."""
    monkeypatch.setattr(environment, "has_locale", lambda _name, _category=None: True)
    marker = environment.requires_locale("xx_XX.utf8", locale.LC_CTYPE)
    assert marker.mark.args[0] is False


def test_requires_tool_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is false when the tool is on PATH."""
    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/tool")
    marker = environment.requires_tool("tool")
    assert marker.mark.args[0] is False
    assert marker.mark.kwargs["reason"] == "requires tool"


def test_requires_tool_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is true when the tool is absent."""
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    marker = environment.requires_tool("tool")
    assert marker.mark.args[0] is True
    assert marker.mark.kwargs["reason"] == "requires tool"


def test_has_jbig2(monkeypatch: pytest.MonkeyPatch) -> None:
    """The JBIG2 probe reflects the dependency probe."""
    monkeypatch.setattr(environment, "jbig2_available", lambda: True)
    assert environment.has_jbig2() is True
    monkeypatch.setattr(environment, "jbig2_available", lambda: False)
    assert environment.has_jbig2() is False


def test_requires_jbig2_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is true when the encoder is missing."""
    monkeypatch.setattr(environment, "jbig2_available", lambda: False)
    marker = environment.requires_jbig2()
    assert marker.mark.args[0] is True
    assert marker.mark.kwargs["reason"] == "jbig2 encoder not installed"


def test_requires_jbig2_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is false when the encoder is present."""
    monkeypatch.setattr(environment, "jbig2_available", lambda: True)
    marker = environment.requires_jbig2()
    assert marker.mark.args[0] is False


def test_has_pillow_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Pillow feature probe returns the checker's boolean."""
    monkeypatch.setattr(environment.features, "check", lambda _name: True)
    assert environment.has_pillow_feature("jpg_2000") is True
    monkeypatch.setattr(environment.features, "check", lambda _name: False)
    assert environment.has_pillow_feature("jpg_2000") is False


def test_requires_pillow_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is true when the feature is absent."""
    monkeypatch.setattr(environment.features, "check", lambda _name: False)
    marker = environment.requires_pillow_feature("jpg_2000", "JPEG 2000")
    assert marker.mark.args[0] is True
    assert marker.mark.kwargs["reason"] == "Pillow built without JPEG 2000 support"


def test_requires_pillow_feature_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker is false when the feature is present."""
    monkeypatch.setattr(environment.features, "check", lambda _name: True)
    marker = environment.requires_pillow_feature("jpg_2000", "JPEG 2000")
    assert marker.mark.args[0] is False
