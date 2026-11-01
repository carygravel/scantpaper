"""Audit test code for statements the test suite never executes.

The coverage gate reports only the shipped ``scantpaper`` package; test
modules are omitted from the reported total by ``[tool.coverage.report]``.
Their execution data is still recorded, so this audit reads the same
``.coverage`` file and fails when a test module was not imported or still
contains an unexecuted statement. Partial branches are ratcheted at the
recorded baseline, so a newly dead branch is visible without reclassifying
existing defensive branches.

Run after the complete suite:

    pytest && python3 dev/check_test_coverage.py

The audit is deliberately not part of the gate. A partial local run leaves
most modules unmeasured, and Debian lacks optional tooling whose skips are
environment facts rather than dead code.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import NamedTuple, cast

import coverage

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = (
    REPO_ROOT / "src" / "scantpaper" / "tests",
    REPO_ROOT / "dev" / "tests",
)

# Partial branches in test code at adoption. Ratchet this DOWN as branches are
# exercised; raise it only when a defensive branch is deliberately added.
PARTIAL_BRANCH_BASELINE = 85


class AuditResult(NamedTuple):
    """Outcome of auditing the test modules against recorded coverage."""

    module_count: int
    missing_statements: int
    partial_branches: int
    errors: list[str]


def iter_test_modules(roots: tuple[Path, ...] = TEST_ROOTS) -> list[Path]:
    """Return every Python module under the test roots, sorted by path."""
    return sorted(path for root in roots for path in root.rglob("*.py"))


def _display(module: Path) -> str:
    """Return a module path relative to the repository when possible."""
    try:
        return str(module.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(module)


def load_report(data_file: Path) -> dict[Path, dict[str, object]]:
    """Read execution data as a JSON report keyed by resolved path.

    ``config_file=False`` keeps the project's report-level omit from hiding
    test modules. The default coverage exclusions (pragma markers and
    ``if TYPE_CHECKING:``) still apply, matching the gate.
    """
    cov = coverage.Coverage(
        config_file=False,
        data_file=str(data_file),
        branch=True,
    )
    cov.load()
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "coverage.json"
        cov.json_report(outfile=str(report_path))
        data = cast(
            "dict[str, object]",
            json.loads(report_path.read_text(encoding="utf-8")),
        )
    files = cast("dict[str, object]", data["files"])
    return {
        Path(name).resolve(): cast("dict[str, object]", entry)
        for name, entry in files.items()
    }


def audit(
    modules: list[Path],
    report: dict[Path, dict[str, object]],
    baseline: int = PARTIAL_BRANCH_BASELINE,
) -> AuditResult:
    """Audit ``modules`` against a JSON coverage report."""
    errors: list[str] = []
    missing_total = 0
    partial_total = 0

    for module in modules:
        entry = report.get(module.resolve())
        if entry is None:
            errors.append(f"{_display(module)}: not measured (module was not imported)")
            continue

        missing = cast("list[int]", entry["missing_lines"])
        if missing:
            missing_total += len(missing)
            lines = ", ".join(str(line) for line in missing)
            errors.append(
                f"{_display(module)}: {len(missing)} unexecuted statement(s) at {lines}"
            )

        summary = cast("dict[str, object]", entry["summary"])
        partial_total += cast("int", summary["num_partial_branches"])

    if partial_total > baseline:
        errors.append(
            f"test partial branches {partial_total} exceed baseline {baseline}"
        )

    return AuditResult(
        module_count=len(modules),
        missing_statements=missing_total,
        partial_branches=partial_total,
        errors=errors,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the test-code audit and return a process exit status."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-file",
        type=Path,
        default=REPO_ROOT / ".coverage",
        help="Coverage data file (default: .coverage in the repository root)",
    )
    parser.add_argument(
        "--partial-branch-baseline",
        type=int,
        default=PARTIAL_BRANCH_BASELINE,
        help="Maximum allowed partial branches in test code",
    )
    args = parser.parse_args(argv)

    if not args.data_file.is_file():
        print(
            f"[FAIL] coverage data {args.data_file} is missing; "
            "run the full pytest suite first"
        )
        return 1

    try:
        report = load_report(args.data_file)
    except coverage.CoverageException as error:
        print(f"[FAIL] cannot read {args.data_file}: {error}")
        return 1

    result = audit(iter_test_modules(), report, args.partial_branch_baseline)
    for error in result.errors:
        print(f"[FAIL] {error}")

    print(
        f"Audited {result.module_count} test modules: "
        f"{result.missing_statements} unexecuted statements, "
        f"{result.partial_branches} partial branches "
        f"(baseline {args.partial_branch_baseline})."
    )
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
