"""Tests for the shared translation policy in dev/translation_policy.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY = REPO_ROOT / "dev" / "translation_policy.py"


def _load_policy() -> ModuleType:
    """Import dev/translation_policy.py directly, bypassing the namespace."""
    spec = importlib.util.spec_from_file_location("translation_policy", str(POLICY))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["translation_policy"] = module
    spec.loader.exec_module(module)
    return module


POLICY_MODULE = _load_policy()


def test_six_provenance_classes() -> None:
    """The ledger accepts exactly the six documented classes."""
    assert POLICY_MODULE.PROVENANCE_CLASSES == (
        "human-historical",
        "human-review",
        "in-project-rebase",
        "tm-consensus",
        "machine-strong",
        "machine-weak",
    )


def test_human_and_machine_classes_partition_the_set() -> None:
    """Every class is either human-origin or machine-origin, never both."""
    human = POLICY_MODULE.HUMAN_PROVENANCE_CLASSES
    machine = POLICY_MODULE.MACHINE_PROVENANCE_CLASSES
    assert human.isdisjoint(machine)
    assert human | machine == set(POLICY_MODULE.PROVENANCE_CLASSES)
    assert POLICY_MODULE.is_machine_class("machine-strong")
    assert not POLICY_MODULE.is_machine_class("human-review")


def test_unknown_class_is_rejected() -> None:
    """An unknown class raises instead of being treated as approved."""
    with pytest.raises(ValueError, match="unknown provenance class"):
        POLICY_MODULE.validate_provenance_class("machine-perfect")


def test_menu_action_is_high_impact() -> None:
    """A menu label without a destructive verb is still a menu action."""
    assert POLICY_MODULE.is_high_impact("_Rename…", [("menu.ui", "24")])


def test_destructive_verb_is_high_impact() -> None:
    """A destructive action label is high-impact wherever it is used."""
    assert POLICY_MODULE.is_high_impact("Delete", [("app.ui", "393")])
    assert POLICY_MODULE.is_high_impact("Clears all pages", [("app.ui", "523")])


def test_tooltip_is_not_high_impact() -> None:
    """A descriptive tooltip is not an action merely because it is in a .ui."""
    assert not POLICY_MODULE.is_high_impact("Use the pan tool", [("app.ui", "657")])


def test_dialog_error_is_high_impact() -> None:
    """A data-loss warning in a dialog is high-impact."""
    assert POLICY_MODULE.is_high_impact(
        "Cannot delete all paper sizes", [("dialog/paperlist.py", "73")]
    )


def test_benign_dialog_label_is_not_high_impact() -> None:
    """A dialog occurrence alone does not make an ordinary label high-impact."""
    assert not POLICY_MODULE.is_high_impact(
        "Page Range", [("dialog/__init__.py", "67")]
    )


def test_long_description_with_destructive_word_is_not_high_impact() -> None:
    """A long sentence is a description, not a destructive action label."""
    msgid = (
        "The available space is less than the value set here, so the scan "
        "may stop before the pages are saved."
    )
    assert not POLICY_MODULE.is_high_impact(msgid, [("dialog/preferences.py", "279")])


def test_occurrences_may_be_bare_paths() -> None:
    """A caller may pass paths rather than polib (path, line) tuples."""
    assert POLICY_MODULE.is_high_impact("_Quit", ["menu.ui"])


def test_placeholder_tokens_cover_printf_and_format_fields() -> None:
    """Both printf and str.format placeholders are extracted."""
    text = "%d pages of %(total)s in {name}"
    assert POLICY_MODULE.placeholder_tokens(text) == ["%d", "%(total)", "{name}"]


def test_spaced_printf_is_a_placeholder_defect() -> None:
    """A space after % is a latent runtime defect the audit can repair."""
    assert POLICY_MODULE.has_spaced_printf("Errore: % s")
    assert POLICY_MODULE.fixes_placeholder_defect(
        "Error: %s", "Errore: % s", "Errore: %s"
    )


def test_mechanical_rebase_accepts_placeholder_whitespace() -> None:
    """A placeholder-spacing fix changes no translated word."""
    assert POLICY_MODULE.is_mechanical_rebase(
        "Errore: dispositivo sconosciuto:% s",
        "Errore: dispositivo sconosciuto: %s",
    )


def test_mechanical_rebase_rejects_a_word_change() -> None:
    """Changing a translated word is not a mechanical rebase."""
    assert not POLICY_MODULE.is_mechanical_rebase("Open image file(s)", "Open images")
