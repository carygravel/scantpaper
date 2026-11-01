"""Tests for dev/check_test_coverage.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK = REPO_ROOT / "dev" / "check_test_coverage.py"


def _load_check() -> ModuleType:
    """Import dev/check_test_coverage.py directly, bypassing the dev namespace."""
    spec = importlib.util.spec_from_file_location("check_test_coverage", str(CHECK))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_test_coverage"] = module
    spec.loader.exec_module(module)
    return module


def _entry(missing: tuple[int, ...] = (), partial: int = 0) -> dict[str, object]:
    """Build the JSON-report shape the audit reads for one module."""
    return {
        "missing_lines": list(missing),
        "summary": {"num_partial_branches": partial},
    }


def test_passes_when_every_module_is_measured_and_complete() -> None:
    """Fully executed modules below the partial-branch baseline pass."""
    check = _load_check()
    modules = [Path("/repo/a.py"), Path("/repo/b.py")]
    report = {module: _entry(partial=40) for module in modules}

    result = check.audit(modules, report, baseline=85)

    assert result.errors == []
    assert result.module_count == 2
    assert result.missing_statements == 0
    assert result.partial_branches == 80


def test_unmeasured_module_is_named() -> None:
    """A module absent from the run data fails with its name."""
    check = _load_check()
    measured = Path("/repo/a.py")
    absent = Path("/repo/b.py")

    result = check.audit([measured, absent], {measured: _entry()}, baseline=85)

    assert len(result.errors) == 1
    assert "b.py" in result.errors[0]
    assert "not measured" in result.errors[0]


def test_missing_statement_names_module_and_lines() -> None:
    """An unexecuted statement fails and reports its line numbers."""
    check = _load_check()
    module = Path("/repo/a.py")

    result = check.audit([module], {module: _entry(missing=(12, 14))}, baseline=85)

    assert len(result.errors) == 1
    assert "a.py" in result.errors[0]
    assert "12, 14" in result.errors[0]
    assert result.missing_statements == 2


def test_partial_branches_over_baseline_fail() -> None:
    """One branch above the recorded baseline fails the audit."""
    check = _load_check()
    module = Path("/repo/a.py")

    result = check.audit([module], {module: _entry(partial=86)}, baseline=85)

    assert len(result.errors) == 1
    assert "86" in result.errors[0]
    assert "85" in result.errors[0]
