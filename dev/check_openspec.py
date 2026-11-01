"""Report whether a newer OpenSpec CLI is available and safe to adopt.

The repository pins the OpenSpec CLI in ``dev/openspec-version`` so that a new
upstream validation rule cannot turn CI red without a deliberate bump (see
``AGENTS.md``). This tool answers the question that otherwise waits for a push:
has npm published a newer release, and does this repository pass that release's
own validation?

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

DEFAULT_PIN_FILE = Path("dev/openspec-version")
DEFAULT_REGISTRY_URL = "https://registry.npmjs.org/@fission-ai/openspec/latest"
REQUEST_TIMEOUT = 30

USER_AGENT = "scantpaper-openspec-check/0.1 (+https://github.com/carygravel/scantpaper)"

# The two commands CI runs, in order. ``--archived`` cannot be combined with
# ``--specs``, so they stay separate.
DEFAULT_VALIDATE_COMMANDS = (
    "openspec validate --specs --strict --no-interactive",
    "openspec validate --archived --no-interactive",
)

CURRENT = "current"
UPDATE_SAFE = "update-safe"
UPDATE_BLOCKED = "update-blocked"

_VERSION = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+].*)?$")


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


def read_pin(path: Path) -> str:
    """Return the version recorded in the pin file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        message = f"cannot read the pin file {path}: {error}"
        raise CheckError(message) from error
    version = text.strip()
    if not version:
        message = f"the pin file {path} is empty"
        raise CheckError(message)
    try:
        parse_version(version)
    except CheckError as error:
        message = f"the pin file {path}: {error}"
        raise CheckError(message) from error
    return version


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
    """Return the version the registry reports as ``latest``."""
    try:
        document = json.loads(_read_url(url))
    except ValueError as error:
        message = f"{url} did not return JSON: {error}"
        raise CheckError(message) from error
    if not isinstance(document, dict):
        message = f"{url} did not return a JSON object"
        raise CheckError(message)
    version = document.get("version")
    if not isinstance(version, str):
        message = f"{url} did not report a 'version' string"
        raise CheckError(message)
    try:
        parse_version(version)
    except CheckError as error:
        message = f"{url} reported {version!r}: {error}"
        raise CheckError(message) from error
    return version


def read_installed(command: str = "openspec") -> str | None:
    """Return the version of the CLI found on PATH, or none."""
    try:
        completed = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = completed.stdout.strip()
    return version or None


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


def classify(pinned: str, latest: str, results: list[ValidationResult]) -> str:
    """Return the update state for a pin, a candidate and its validation."""
    if parse_version(latest) <= parse_version(pinned):
        return CURRENT
    if all(result.ok for result in results):
        return UPDATE_SAFE
    return UPDATE_BLOCKED


def _markdown(
    pinned: str,
    installed: str | None,
    latest: str,
    state: str,
    results: list[ValidationResult],
) -> str:
    """Render the report as the body of a GitHub issue."""
    lines = [
        "| | Version |",
        "| --- | --- |",
        f"| Pinned in `dev/openspec-version` | `{pinned}` |",
        f"| Installed wherever this check ran | `{installed or 'unknown'}` |",
        f"| Latest on npm | `{latest}` |",
        "",
    ]
    if state == CURRENT:
        lines.append(f"`{pinned}` is the latest release; nothing to do.")
        return "\n".join(lines)
    verdict = (
        f"**Safe to upgrade:** every validation command passes with `{latest}`."
        if state == UPDATE_SAFE
        else f"**Blocked:** `{latest}` fails this repository's validation."
    )
    lines += [verdict, "", "| Command | Result |", "| --- | --- |"]
    for result in results:
        outcome = "pass" if result.ok else f"fail (exit {result.returncode})"
        lines.append(f"| `{result.command}` | {outcome} |")
    lines.append("")
    failed = next((result for result in results if not result.ok), None)
    if failed is not None:
        lines += [
            f"Output of `{failed.command}`:",
            "",
            "```",
            failed.output or "(no output)",
            "```",
            "",
        ]
    lines += [
        (
            "To adopt it:"
            if state == UPDATE_SAFE
            else "Do not bump the pin yet. Once the failing command passes, adopt it:"
        ),
        "",
        "```sh",
        f"printf '%s\\n' {latest} > dev/openspec-version",
        f"npm install -g @fission-ai/openspec@{latest}",
        "openspec validate --specs --strict --no-interactive",
        "openspec validate --archived --no-interactive",
        "```",
        "",
        "This issue closes itself once the pin matches npm's latest release.",
    ]
    return "\n".join(lines)


def build_report(
    pinned: str,
    installed: str | None,
    latest: str,
    results: list[ValidationResult],
) -> dict[str, object]:
    """Assemble the JSON report, including the Markdown body."""
    state = classify(pinned, latest, results)
    return {
        "pinned": pinned,
        "installed": installed,
        "latest": latest,
        "state": state,
        "changed": state != CURRENT,
        "validations": [
            {
                "command": result.command,
                "ok": result.ok,
                "returncode": result.returncode,
                "output": result.output,
            }
            for result in results
        ],
        "markdown": _markdown(pinned, installed, latest, state, results),
        "summary": _summary(pinned, installed, latest, state, results),
    }


def _summary(
    pinned: str,
    installed: str | None,
    latest: str,
    state: str,
    results: list[ValidationResult],
) -> str:
    """Render the report for a human reading a terminal."""
    headline = (
        f"OpenSpec CLI: pinned {pinned}, latest {latest}, "
        f"installed {installed or 'unknown'}"
    )
    if state == CURRENT:
        return f"{headline}\n  up to date: nothing to do"
    verdict = (
        "safe to upgrade"
        if state == UPDATE_SAFE
        else "blocked by a failing validation command"
    )
    lines = [headline, f"  update available: {verdict}"]
    for result in results:
        marker = "ok" if result.ok else f"FAILED ({result.returncode})"
        lines.append(f"  {marker}: {result.command}")
    return "\n".join(lines)


def main() -> int:
    """Run the OpenSpec release check."""
    parser = argparse.ArgumentParser(
        description="Report whether a newer OpenSpec CLI is available and safe"
    )
    parser.add_argument(
        "--pin-file",
        type=Path,
        default=DEFAULT_PIN_FILE,
        help=f"File holding the pinned version (default: {DEFAULT_PIN_FILE})",
    )
    parser.add_argument(
        "--registry-url",
        default=DEFAULT_REGISTRY_URL,
        help="Registry document to read the latest version from",
    )
    parser.add_argument(
        "--validate-cmd",
        action="append",
        dest="validate_cmds",
        default=None,
        help=(
            "Command that must pass for the candidate to be safe; repeatable "
            "(default: the two commands CI runs)"
        ),
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path(),
        help="Directory the validation commands run in (default: the current)",
    )
    parser.add_argument(
        "--installed",
        default=None,
        help="Report this installed version instead of running 'openspec --version'",
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

    commands = (
        tuple(args.validate_cmds) if args.validate_cmds else DEFAULT_VALIDATE_COMMANDS
    )
    try:
        pinned = read_pin(args.pin_file)
        latest = fetch_latest(args.registry_url)
    except CheckError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 2
    installed = args.installed if args.installed is not None else read_installed()
    results = (
        run_validations(commands, args.cwd)
        if parse_version(latest) > parse_version(pinned)
        else []
    )
    report = build_report(pinned, installed, latest, results)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.markdown:
        print(report["markdown"])
    else:
        print(report["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
