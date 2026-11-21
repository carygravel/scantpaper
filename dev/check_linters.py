"""Report whether newer ruff or ty releases are available and safe to adopt.

The repository pins the ruff and ty versions that CI installs in
``dev/lint-versions`` so that a new lint rule or ty diagnostic cannot turn CI
red without a deliberate bump. This tool answers the question that otherwise
waits for a push: has PyPI published a newer release, and does this repository
pass its lint and type gates with that release?

It is advisory. A detected update, whether it validates cleanly or not, exits
0 so that the scheduled workflow can file a reminder; only an unreadable pin
file, registry document or candidate version exits non-zero, so "could not
tell" is never reported as "up to date".
"""

from __future__ import annotations

import argparse
import http.client
import json
import re
import shlex
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PIN_FILE = Path("dev/lint-versions")
# PyPI's per-package JSON documents live at one registry address per tool.
REGISTRY_TEMPLATE = "https://pypi.org/pypi/{tool}/json"
REQUEST_TIMEOUT = 30

USER_AGENT = "scantpaper-linter-check/0.1 (+https://github.com/carygravel/scantpaper)"

# The validation commands CI runs for each tool, in order; ``ruff`` runs two
# because ``ruff format --check`` is a separate gate from ``ruff check``.
# ``--validate-cmd`` replaces a tool's entry here, keeping one list per tool
# that a new gate can extend in a single place.
DEFAULT_VALIDATE_COMMANDS: dict[str, tuple[str, ...]] = {
    "ruff": ("ruff check .", "ruff format --check ."),
    "ty": ("ty check .",),
}

CURRENT = "current"
UPDATE_SAFE = "update-safe"
UPDATE_BLOCKED = "update-blocked"

_VERSION = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+].*)?$")
_VERSION_IN_TEXT = re.compile(r"\d+\.\d+\.\d+")
_WARNING = re.compile(r"^warning:", re.IGNORECASE)


class CheckError(Exception):
    """Raised when the state cannot be determined."""


@dataclass
class ValidationResult:
    """The outcome of running one validation command."""

    command: str
    returncode: int
    output: str

    @property
    def ok(self) -> bool:
        """Return whether the command succeeded."""
        return self.returncode == 0


@dataclass
class ToolStatus:
    """One tool's versions, validation results and verdict."""

    pinned: str
    installed: str | None
    latest: str
    validations: list[ValidationResult]
    state: str

    @property
    def changed(self) -> bool:
        """Return whether the latest release differs from the pin."""
        return parse_version(self.latest) > parse_version(self.pinned)


def parse_version(text: str) -> tuple[int, int, int]:
    """Return the numeric parts of a release version."""
    match = _VERSION.match(text.strip())
    if match is None:
        message = f"{text.strip()!r} is not a release version"
        raise CheckError(message)
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def read_pins(path: Path) -> dict[str, str]:
    """Return the tool-to-version mapping recorded in the pin file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read the pin file {path}: {error}"
        raise CheckError(message) from error
    pins: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "=" not in stripped:
            message = f"the pin file {path} has an unexpected line: {stripped!r}"
            raise CheckError(message)
        tool, version = stripped.split("=", 1)
        tool = tool.strip()
        version = version.strip()
        if not tool or not version:
            message = (
                f"the pin file {path} has an empty tool or version in {stripped!r}"
            )
            raise CheckError(message)
        try:
            parse_version(version)
        except CheckError as error:
            message = f"the pin file {path}: {error}"
            raise CheckError(message) from error
        pins[tool] = version
    if not pins:
        message = f"the pin file {path} is empty"
        raise CheckError(message)
    return pins


def parse_validate_cmds(
    values: list[str] | None,
) -> dict[str, tuple[str, ...]]:
    """Return per-tool validation command lists from ``--validate-cmd`` pairs."""
    overrides: dict[str, list[str]] = {}
    for item in values or ():
        if "=" not in item:
            message = f"--validate-cmd must be tool=command, got {item!r}"
            raise CheckError(message)
        tool, command = item.split("=", 1)
        tool = tool.strip()
        command = command.strip()
        if not tool or not command:
            message = f"--validate-cmd has an empty tool or command in {item!r}"
            raise CheckError(message)
        overrides.setdefault(tool, []).append(command)
    return {tool: tuple(commands) for tool, commands in overrides.items()}


def _read_url(url: str) -> bytes:
    """Return the body of a ``file``, ``http`` or ``https`` URL."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "file":
        path = Path(urllib.parse.unquote(parts.path))
        try:
            return path.read_bytes()
        except OSError as error:
            message = f"cannot read {path}: {error}"
            raise CheckError(message) from error
    if parts.scheme not in ("http", "https"):
        message = f"{url} is not a file, http or https URL"
        raise CheckError(message)
    connection: http.client.HTTPConnection
    if parts.scheme == "https":
        connection = http.client.HTTPSConnection(parts.netloc, timeout=REQUEST_TIMEOUT)
    else:
        connection = http.client.HTTPConnection(parts.netloc, timeout=REQUEST_TIMEOUT)
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    try:
        connection.request(
            "GET",
            target,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        response = connection.getresponse()
        body = response.read()
        status = response.status
    except (OSError, http.client.HTTPException) as error:
        message = f"cannot read {url}: {error}"
        raise CheckError(message) from error
    finally:
        connection.close()
    if status != http.client.OK:
        message = f"{url} returned HTTP {status}"
        raise CheckError(message)
    return body


def fetch_latest(url: str) -> str:
    """Return the version PyPI reports as the latest release."""
    try:
        document = json.loads(_read_url(url))
    except ValueError as error:
        message = f"{url} did not return JSON: {error}"
        raise CheckError(message) from error
    if not isinstance(document, dict):
        message = f"{url} did not return a JSON object"
        raise CheckError(message)
    info = document.get("info")
    if not isinstance(info, dict):
        message = f"{url} did not report an 'info' object"
        raise CheckError(message)
    version = info.get("version")
    if not isinstance(version, str):
        message = f"{url} did not report a 'version' string"
        raise CheckError(message)
    try:
        parse_version(version)
    except CheckError as error:
        message = f"{url} reported {version!r}: {error}"
        raise CheckError(message) from error
    return version


def read_installed(tool: str) -> str | None:
    """Return the version of a tool found on PATH, or none."""
    try:
        completed = subprocess.run(
            [tool, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (completed.stdout + completed.stderr).strip()
    match = _VERSION_IN_TEXT.search(output)
    return match.group(0) if match else (output or None)


def run_validations(commands: tuple[str, ...], cwd: Path) -> list[ValidationResult]:
    """Run each command, stopping at the first failure."""
    results: list[ValidationResult] = []
    for command in commands:
        try:
            completed = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=False,
                cwd=cwd,
                timeout=600,
            )
        except (OSError, subprocess.SubprocessError) as error:
            results.append(
                ValidationResult(command, 124, f"cannot run {command!r}: {error}")
            )
            break
        output = (completed.stdout + completed.stderr).strip()
        results.append(ValidationResult(command, completed.returncode, output))
        if completed.returncode != 0:
            break
    return results


def collect_warnings(validations: list[ValidationResult]) -> list[str]:
    """Return the warning lines a tool's validation commands printed."""
    warnings: list[str] = []
    for result in validations:
        for line in result.output.splitlines():
            split = line.strip()
            if _WARNING.match(split) and split not in warnings:
                warnings.append(split)
    return warnings


def classify(pinned: str, latest: str, results: list[ValidationResult]) -> str:
    """Return the update state for a pin, a candidate and its validation."""
    if parse_version(latest) <= parse_version(pinned):
        return CURRENT
    if all(result.ok for result in results):
        return UPDATE_SAFE
    return UPDATE_BLOCKED


def _tool_lines(tools: dict[str, ToolStatus]) -> list[str]:
    """Return the per-tool table rows for Markdown."""
    lines = [
        "| Tool | Pinned | Installed | Latest | State |",
        "| --- | --- | --- | --- | --- |",
    ]
    for tool, status in sorted(tools.items()):
        lines.append(
            f"| `{tool}` | `{status.pinned}` | "
            f"`{status.installed or 'unknown'}` | `{status.latest}` | "
            f"`{status.state}` |"
        )
    return lines


def _bump_commands(tools: dict[str, ToolStatus]) -> list[str]:
    """Return the ``sed`` commands that adopt every changed candidate."""
    commands: list[str] = []
    for tool, status in sorted(tools.items()):
        if status.changed:
            commands.append(
                f"sed -i 's/^{tool}=.*/{tool}={status.latest}/' {DEFAULT_PIN_FILE}"
            )
    return commands


def _markdown(tools: dict[str, ToolStatus], overall: str) -> str:
    """Render the report as the body of a GitHub issue."""
    lines = [*_tool_lines(tools), ""]
    if overall == CURRENT:
        lines.append("Every pin matches the latest release; nothing to do.")
        return "\n".join(lines)
    lines += [
        "| Command | Tool | Result |",
        "| --- | --- | --- |",
    ]
    for tool, status in sorted(tools.items()):
        for result in status.validations:
            outcome = "pass" if result.ok else f"fail (exit {result.returncode})"
            lines.append(f"| `{result.command}` | `{tool}` | {outcome} |")
    warnings = {
        tool: collect_warnings(status.validations)
        for tool, status in sorted(tools.items())
    }
    if any(warnings.values()):
        lines += [
            "",
            "Config-migration warnings (the bump may need a `pyproject.toml` change):",
            "",
        ]
        for tool, found in warnings.items():
            for warning in found:
                lines.append(f"- `{tool}`: `{warning}`")
    failed = [
        (tool, result)
        for tool, status in sorted(tools.items())
        for result in status.validations
        if not result.ok
    ]
    if failed:
        lines += [
            "",
            f"Output of `{failed[0][1].command}` (tool `{failed[0][0]}`):",
            "",
        ]
        lines += ["```", failed[0][1].output or "(no output)", "```"]
    commands = _bump_commands(tools)
    verdict = "safe to upgrade" if overall == UPDATE_SAFE else "blocked"
    lines += [
        "",
        f"**Overall: {overall} ({verdict}).** To adopt the newer releases:",
        "",
        "```sh",
        *commands,
        "python3 -m pytest",
        "```",
        "",
        "This issue closes itself once every pin matches the latest release.",
    ]
    return "\n".join(lines)


def _summary(tools: dict[str, ToolStatus], overall: str) -> str:
    """Render the report for a human reading a terminal."""
    lines = [f"Lint tools: {len(tools)} checked, overall {overall}"]
    for tool, status in sorted(tools.items()):
        headline = (
            f"  {tool}: pinned {status.pinned}, installed "
            f"{status.installed or 'unknown'}, latest {status.latest}"
        )
        if status.state == CURRENT:
            lines.append(f"{headline}\n    up to date: nothing to do")
        else:
            verdict = (
                "safe to upgrade"
                if status.state == UPDATE_SAFE
                else "blocked by a failing validation command"
            )
            lines.append(f"{headline}\n    update available: {verdict}")
    return "\n".join(lines)


def build_report(tools: dict[str, ToolStatus]) -> dict[str, object]:
    """Assemble the JSON report, including the Markdown body."""
    states = [status.state for status in tools.values()]
    overall = (
        UPDATE_BLOCKED
        if UPDATE_BLOCKED in states
        else UPDATE_SAFE
        if UPDATE_SAFE in states
        else CURRENT
    )
    return {
        "tools": {
            tool: {
                "pinned": status.pinned,
                "installed": status.installed,
                "latest": status.latest,
                "state": status.state,
                "changed": status.changed,
                "warnings": collect_warnings(status.validations),
                "validations": [
                    {
                        "command": result.command,
                        "ok": result.ok,
                        "returncode": result.returncode,
                        "output": result.output,
                    }
                    for result in status.validations
                ],
            }
            for tool, status in sorted(tools.items())
        },
        "state": overall,
        "changed": overall != CURRENT,
        "markdown": _markdown(tools, overall),
        "summary": _summary(tools, overall),
    }


def _registry_overrides(values: list[str] | None) -> dict[str, str]:
    """Return per-tool registry URLs from ``--registry-url`` pairs."""
    overrides: dict[str, str] = {}
    for item in values or ():
        if "=" not in item:
            message = f"--registry-url must be tool=url, got {item!r}"
            raise CheckError(message)
        tool, url = item.split("=", 1)
        tool = tool.strip()
        url = url.strip()
        if not tool or not url:
            message = f"--registry-url has an empty tool or url in {item!r}"
            raise CheckError(message)
        overrides[tool] = url
    return overrides


def _installed_overrides(values: list[str] | None) -> dict[str, str]:
    """Return per-tool installed-version overrides from ``--installed`` pairs."""
    overrides: dict[str, str] = {}
    for item in values or ():
        if "=" not in item:
            message = f"--installed must be tool=version, got {item!r}"
            raise CheckError(message)
        tool, version = item.split("=", 1)
        tool = tool.strip()
        version = version.strip()
        if not tool or not version:
            message = f"--installed has an empty tool or version in {item!r}"
            raise CheckError(message)
        overrides[tool] = version
    return overrides


def _select_tools(pins: dict[str, str], tool: str | None) -> tuple[str, ...]:
    """Return the tools to check, rejecting a filter unknown to the pin."""
    selected = (tool,) if tool is not None else tuple(pins)
    unknown = [name for name in selected if name not in pins]
    if unknown:
        message = f"tool(s) not in the pin file: {', '.join(unknown)}"
        raise CheckError(message)
    return selected


def main() -> int:
    """Run the linter release check."""
    parser = argparse.ArgumentParser(
        description="Report whether newer ruff or ty releases are safe to adopt"
    )
    parser.add_argument(
        "--pin-file",
        type=Path,
        default=DEFAULT_PIN_FILE,
        help=f"File holding the pinned tool versions (default: {DEFAULT_PIN_FILE})",
    )
    parser.add_argument(
        "--tool",
        default=None,
        help="Check only this tool, instead of every pinned tool",
    )
    parser.add_argument(
        "--registry-url",
        action="append",
        default=None,
        help=(
            "Registry document for one tool as tool=url; repeatable. Defaults "
            "to PyPI's per-tool JSON address"
        ),
    )
    parser.add_argument(
        "--validate-cmd",
        action="append",
        dest="validate_cmds",
        default=None,
        help=(
            "Validation command as tool=command; repeatable. Replaces that "
            "tool's default commands (ruff: 'ruff check .' and 'ruff format "
            "--check .'; ty: 'ty check .')"
        ),
    )
    parser.add_argument(
        "--installed",
        action="append",
        default=None,
        help="Report this installed version as tool=version; repeatable",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path(),
        help="Directory the validation commands run in (default: the current)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON, for the workflow to consume",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Emit the issue body as Markdown",
    )
    args = parser.parse_args()

    try:
        pins = read_pins(args.pin_file)
        selected = _select_tools(pins, args.tool)
        overrides = parse_validate_cmds(args.validate_cmds)
        installed = _installed_overrides(args.installed)
        registries = _registry_overrides(args.registry_url)
        tools: dict[str, ToolStatus] = {}
        for tool in selected:
            url = registries.get(tool) or REGISTRY_TEMPLATE.format(tool=tool)
            latest = fetch_latest(url)
            commands = (
                overrides[tool]
                if tool in overrides
                else DEFAULT_VALIDATE_COMMANDS.get(tool, ())
            )
            results = (
                run_validations(commands, args.cwd)
                if parse_version(latest) > parse_version(pins[tool])
                else []
            )
            tools[tool] = ToolStatus(
                pinned=pins[tool],
                installed=installed.get(
                    tool,
                    read_installed(tool),
                ),
                latest=latest,
                validations=results,
                state=classify(pins[tool], latest, results),
            )
    except CheckError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2

    report = build_report(tools)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(report["markdown"])
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
