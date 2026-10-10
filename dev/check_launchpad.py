"""Report Launchpad translation changes against a committed baseline.

Launchpad exposes the state of the `scantpaper` translation template and of
each language without authentication, but nothing tells the maintainer when
that state has moved between releases. This tool answers "has anything changed
on Launchpad since we last pulled the catalogs?" by comparing the current
state against a snapshot committed as `po/launchpad-state.json`.

It watches two independent triggers, each read from the only public surface
that carries it:

* the **template** (the message set / `.pot`), from the Launchpad JSON API
  resource for the template, using `date_last_updated` and the HTTP entity tag
  with a conditional request (an unchanged template costs a `304`);
* **per-language translation activity**, from the series translation page,
  whose per-language last-changed timestamps exist nowhere else. That page is
  read on every run, because a translation can change without the template
  changing.

The tool never downloads a catalog: every Launchpad `+export` endpoint requires
a logged-in session. It also never authenticates. It is advisory by default:
finding a change is not an error, so the exit status is zero either way and CI
opts into `--fail-on-change`. A state that genuinely could not be read is
reported as "could not determine" and exits non-zero, which is deliberately
distinct from "unchanged".

The baseline is a sampled snapshot of what Launchpad reported, not something
derived from git, and is advanced only by an explicit `--update` run after the
catalogs have been synced (see `release_procedure.md`).

Usage:
    python3 dev/check_launchpad.py [--json] [--fail-on-change]
    python3 dev/check_launchpad.py --update [--dry-run]
"""

from __future__ import annotations

import argparse
import datetime
import http.client
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import cast

from typing_extensions import override

REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_API_URL = "https://api.launchpad.net/devel/scantpaper/trunk/+pots/scantpaper"
DEFAULT_HTML_URL = "https://translations.launchpad.net/scantpaper/trunk/+translations"
DEFAULT_BASELINE = REPO_ROOT / "po" / "launchpad-state.json"

SERIES = "trunk"
POT = "scantpaper"

USER_AGENT = (
    "scantpaper-translation-check/0.1 (+https://github.com/carygravel/scantpaper)"
)

HTTP_OK = 200
HTTP_NOT_MODIFIED = 304

REQUEST_TIMEOUT = 30

# The per-language link on the series page, from which the language code is
# taken. The `$` keeps it from matching the `?show=...` links in the same row.
_LANGUAGE_ANCHOR = re.compile(r"/\+pots/[^/]+/(?P<lang>[A-Za-z0-9_@.+-]+)/\+translate$")


class LaunchpadError(Exception):
    """An error whose message is safe to show the user."""


@dataclass(frozen=True)
class TemplateState:
    """The template's message-set state as Launchpad reports it."""

    date_last_updated: str
    etag: str


@dataclass(frozen=True)
class LanguageState:
    """One language's activity as the series page reports it."""

    last_changed: str
    untranslated: int
    suggestions: int


@dataclass
class CheckResult:
    """The outcome of comparing Launchpad against the baseline."""

    template: TemplateState | None
    languages: dict[str, LanguageState] | None
    problems: list[str]
    template_changed: bool
    changed_languages: dict[str, LanguageState]
    new_languages: dict[str, LanguageState]

    @property
    def determined(self) -> bool:
        """Return True when every part of the upstream state was read."""
        return not self.problems

    @property
    def changed(self) -> bool:
        """Return True when any unit differs from the baseline."""
        return (
            self.template_changed
            or bool(self.changed_languages)
            or bool(self.new_languages)
        )


class _TranslationPageParser(HTMLParser):
    """Extract one record per language from the series translation page.

    The parser keys on the anchors the page emits (the per-language
    `…/<lang>/+translate` link plus the optional `?show=untranslated` and
    `?show=new_suggestions` links) and on the `<time>` element, not on
    presentational class names.
    """

    def __init__(self) -> None:
        """Initialise the parser's row and anchor state."""
        super().__init__()
        self.languages: dict[str, LanguageState] = {}
        self._row: dict[str, object] = {}
        self._href: str | None = None
        self._text: list[str] = []
        self._in_anchor = False

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Begin a table row, an anchor, or a timestamp element."""
        if tag == "tr":
            self._row = {}
        elif tag == "a":
            self._in_anchor = True
            self._href = dict(attrs).get("href")
            self._text = []
        elif tag == "time":
            moment = dict(attrs).get("datetime")
            if moment is not None:
                self._row["last_changed"] = _normalise_moment(moment)

    @override
    def handle_data(self, data: str) -> None:
        """Collect the text of the anchor currently in progress."""
        if self._in_anchor:
            self._text.append(data)

    @override
    def handle_endtag(self, tag: str) -> None:
        """Classify a finished anchor, or record a finished row."""
        if tag == "a":
            self._close_anchor()
        elif tag == "tr":
            self._close_row()

    def _close_anchor(self) -> None:
        """Attach the finished anchor's meaning to the current row."""
        href = self._href or ""
        text = "".join(self._text).strip()
        self._in_anchor = False
        self._href = None
        match = _LANGUAGE_ANCHOR.search(href)
        if match is not None:
            self._row["code"] = match.group("lang")
        elif href.endswith("show=untranslated"):
            self._row["untranslated"] = _as_count(text)
        elif href.endswith("show=new_suggestions"):
            self._row["suggestions"] = _as_count(text)

    def _close_row(self) -> None:
        """Record the row's language when it carries a code and a timestamp."""
        code = self._row.get("code")
        last_changed = self._row.get("last_changed")
        if isinstance(code, str) and isinstance(last_changed, str):
            self.languages[code] = LanguageState(
                last_changed=last_changed,
                untranslated=_as_count(self._row.get("untranslated")),
                suggestions=_as_count(self._row.get("suggestions")),
            )
        self._row = {}


def _normalise_moment(value: str) -> str:
    """Reduce an ISO timestamp to ``YYYY-MM-DD HH:MM:SS`` (UTC)."""
    return value[:19].replace("T", " ")


def _as_count(value: object) -> int:
    """Coerce a page value to a non-negative count, defaulting to zero."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def parse_languages(html: str) -> dict[str, LanguageState]:
    """Extract one record per language from a series translation page."""
    parser = _TranslationPageParser()
    parser.feed(html)
    parser.close()
    return parser.languages


def _get(url: str, *, etag: str | None = None) -> tuple[int, bytes]:
    """Fetch ``url``, returning (status, body); a `304` yields an empty body.

    Only `http`, `https` and `file` URLs are supported. Sending the baseline
    entity tag as `If-None-Match` lets an unchanged template answer `304`
    without a body.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.scheme == "file":
        return HTTP_OK, _read_file(urllib.parse.unquote(parts.path))
    if parts.scheme not in ("http", "https"):
        message = f"unsupported URL scheme in {url!r}"
        raise LaunchpadError(message)
    return _request(url, parts, etag)


def _read_file(path_text: str) -> bytes:
    """Read a local file, converting OS errors into a LaunchpadError."""
    try:
        return Path(path_text).read_bytes()
    except OSError as error:
        message = f"cannot read {path_text}: {error}"
        raise LaunchpadError(message) from error


def _request(
    url: str, parts: urllib.parse.SplitResult, etag: str | None
) -> tuple[int, bytes]:
    """Perform one HTTP(S) GET and return (status, body)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json, text/html"}
    if etag is not None:
        headers["If-None-Match"] = etag
    target = parts.path or "/"
    if parts.query:
        target = f"{target}?{parts.query}"
    if parts.scheme == "https":
        connection = http.client.HTTPSConnection(parts.netloc, timeout=REQUEST_TIMEOUT)
    else:
        connection = http.client.HTTPConnection(parts.netloc, timeout=REQUEST_TIMEOUT)
    try:
        connection.request("GET", target, headers=headers)
        response = connection.getresponse()
        status = response.status
        body = response.read()
    except (OSError, http.client.HTTPException) as error:
        message = f"request to {url} failed: {error}"
        raise LaunchpadError(message) from error
    finally:
        connection.close()
    return status, body


def _parse_template(body: bytes) -> TemplateState:
    """Parse the template resource JSON into a TemplateState."""
    try:
        data = json.loads(body)
    except ValueError as error:
        message = f"the template response is not JSON: {error}"
        raise LaunchpadError(message) from error
    date = data.get("date_last_updated") if isinstance(data, dict) else None
    etag = data.get("http_etag") if isinstance(data, dict) else None
    if not isinstance(date, str) or not isinstance(etag, str):
        message = "the template response is missing date_last_updated or http_etag"
        raise LaunchpadError(message)
    return TemplateState(date_last_updated=date, etag=etag)


def _read_template(
    api_url: str, baseline: dict[str, object]
) -> tuple[TemplateState | None, str | None]:
    """Fetch the template resource; return (state, problem)."""
    previous = baseline.get("template")
    etag = previous.get("etag") if isinstance(previous, dict) else None
    if not isinstance(etag, str):
        etag = None
    try:
        status, body = _get(api_url, etag=etag)
    except LaunchpadError as error:
        return None, f"the template ({api_url}): {error}"
    if status == HTTP_NOT_MODIFIED:
        if isinstance(previous, dict):
            date = previous.get("date_last_updated")
            tag = previous.get("etag")
            if isinstance(date, str) and isinstance(tag, str):
                return TemplateState(date_last_updated=date, etag=tag), None
        return None, f"the template ({api_url}): 304 with no usable baseline entry"
    try:
        return _parse_template(body), None
    except LaunchpadError as error:
        return None, f"the template ({api_url}): {error}"


def _read_languages(
    html_url: str,
) -> tuple[dict[str, LanguageState] | None, str | None]:
    """Fetch and parse the series page; return (languages, problem)."""
    try:
        _, body = _get(html_url)
    except LaunchpadError as error:
        return None, f"the languages ({html_url}): {error}"
    languages = parse_languages(body.decode("utf-8", "replace"))
    if not languages:
        return None, f"the languages ({html_url}): no language rows were parsed"
    return languages, None


def load_baseline(path: Path) -> dict[str, object]:
    """Read the committed baseline, or an empty document if it is absent."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        message = f"cannot read baseline {path}: {error}"
        raise LaunchpadError(message) from error
    if not isinstance(data, dict):
        message = f"baseline {path} is not a JSON object"
        raise LaunchpadError(message)
    return cast("dict[str, object]", data)


def _template_changed(baseline: dict[str, object], template: TemplateState) -> bool:
    """Return True when the template differs from the baseline entry."""
    previous = baseline.get("template")
    if not isinstance(previous, dict):
        return True
    return bool(
        previous.get("etag") != template.etag
        or previous.get("date_last_updated") != template.date_last_updated
    )


def _changed_languages(
    baseline: dict[str, object], languages: dict[str, LanguageState]
) -> tuple[dict[str, LanguageState], dict[str, LanguageState]]:
    """Return the (changed, new) languages relative to the baseline."""
    previous = baseline.get("languages")
    known = previous if isinstance(previous, dict) else {}
    changed: dict[str, LanguageState] = {}
    new: dict[str, LanguageState] = {}
    for code, state in languages.items():
        old = known.get(code)
        if not isinstance(old, dict):
            new[code] = state
        elif old.get("last_changed") != state.last_changed:
            changed[code] = state
    return changed, new


def run_check(
    baseline: dict[str, object], *, api_url: str, html_url: str
) -> CheckResult:
    """Read both public surfaces and compare them against the baseline."""
    problems: list[str] = []
    template, template_problem = _read_template(api_url, baseline)
    if template_problem is not None:
        problems.append(template_problem)
    languages, languages_problem = _read_languages(html_url)
    if languages_problem is not None:
        problems.append(languages_problem)

    template_changed = template is not None and _template_changed(baseline, template)
    if languages is None:
        changed: dict[str, LanguageState] = {}
        new: dict[str, LanguageState] = {}
    else:
        changed, new = _changed_languages(baseline, languages)

    return CheckResult(
        template=template,
        languages=languages,
        problems=problems,
        template_changed=template_changed,
        changed_languages=changed,
        new_languages=new,
    )


def _language_line(code: str, state: LanguageState, status: str) -> str:
    """Format one language's change as a report line."""
    return (
        f"  {code} ({status}): {state.last_changed}, "
        f"{state.untranslated} untranslated, {state.suggestions} suggestions"
    )


def _report(result: CheckResult, baseline: dict[str, object]) -> None:
    """Print the human-readable report."""
    if result.changed:
        print("Launchpad translation changes since the baseline:")
        if result.template_changed and result.template is not None:
            print(f"  template: {result.template.date_last_updated}")
        for code, state in sorted(result.changed_languages.items()):
            print(_language_line(code, state, "changed"))
        for code, state in sorted(result.new_languages.items()):
            print(_language_line(code, state, "new"))
    else:
        captured = baseline.get("captured")
        suffix = f" (captured {captured})" if captured else ""
        print(f"No Launchpad translation changes since the baseline{suffix}.")
    for problem in result.problems:
        print(f"[FAIL] could not determine {problem}")


def _payload(result: CheckResult, baseline: dict[str, object]) -> dict[str, object]:
    """Build the machine-readable report consumed by the workflow."""
    languages: dict[str, object] = {}
    if result.languages is not None:
        for code, state in sorted(result.languages.items()):
            languages[code] = {
                "changed": code in result.changed_languages,
                "new": code in result.new_languages,
                "last_changed": state.last_changed,
                "untranslated": state.untranslated,
                "suggestions": state.suggestions,
            }
    template: dict[str, object] | None = None
    if result.template is not None:
        template = {
            "changed": result.template_changed,
            "date_last_updated": result.template.date_last_updated,
            "etag": result.template.etag,
        }
    return {
        "determined": result.determined,
        "problems": result.problems,
        "changed": result.changed,
        "baseline_captured": baseline.get("captured"),
        "template": template,
        "languages": languages,
    }


def _emit(result: CheckResult, baseline: dict[str, object], *, as_json: bool) -> None:
    """Write the report as JSON or as text."""
    if as_json:
        print(json.dumps(_payload(result, baseline), indent=2, ensure_ascii=False))
    else:
        _report(result, baseline)


def _build_baseline(
    template: TemplateState,
    languages: dict[str, LanguageState],
    now: datetime.datetime,
) -> dict[str, object]:
    """Return the baseline document for the current Launchpad state."""
    return {
        "series": SERIES,
        "pot": POT,
        "captured": now.isoformat(),
        "template": {
            "date_last_updated": template.date_last_updated,
            "etag": template.etag,
        },
        "languages": {
            code: {
                "last_changed": state.last_changed,
                "untranslated": state.untranslated,
                "suggestions": state.suggestions,
            }
            for code, state in sorted(languages.items())
        },
    }


def _apply_update(
    result: CheckResult, path: Path, *, dry_run: bool, now: datetime.datetime
) -> int:
    """Advance the committed baseline, refusing an incomplete read."""
    if result.template is None or result.languages is None:
        print("[FAIL] refusing to update the baseline: the state could not be read")
        for problem in result.problems:
            print(f"[FAIL] could not determine {problem}")
        return 1
    baseline = _build_baseline(result.template, result.languages, now)
    if dry_run:
        print(f"Dry run: would write {path} from the current Launchpad state.")
        return 0
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(baseline, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"[FAIL] cannot write baseline {path}: {error}")
        return 1
    print(f"Updated {path} (captured {baseline['captured']}).")
    return 0


def main() -> int:
    """Run the Launchpad translation check."""
    parser = argparse.ArgumentParser(
        description="Report Launchpad translation changes against a baseline"
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Template JSON API resource (default: the live scantpaper template)",
    )
    parser.add_argument(
        "--html-url",
        default=DEFAULT_HTML_URL,
        help="Series translation page (default: the live trunk page)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Committed baseline file (default: po/launchpad-state.json)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the report as JSON for the workflow to consume",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Advance the baseline to the current state instead of reporting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --update, report what would be written without writing it",
    )
    parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="Exit non-zero when a change is detected (default: advisory)",
    )
    args = parser.parse_args()

    try:
        baseline = load_baseline(args.baseline)
    except LaunchpadError as error:
        print(f"[FAIL] {error}")
        return 1

    result = run_check(baseline, api_url=args.api_url, html_url=args.html_url)
    now = datetime.datetime.now(tz=datetime.timezone.utc)

    if args.update:
        return _apply_update(result, args.baseline, dry_run=args.dry_run, now=now)

    _emit(result, baseline, as_json=args.json)

    if not result.determined:
        return 1
    return 1 if result.changed and args.fail_on_change else 0


if __name__ == "__main__":
    sys.exit(main())
