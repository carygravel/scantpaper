"""Tests for the Launchpad translation check dev/check_launchpad.py."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import TypedDict, cast


class LanguageJson(TypedDict):
    """A language's entry in the JSON report."""

    changed: bool
    new: bool
    last_changed: str
    untranslated: int
    suggestions: int


class TemplateJson(TypedDict):
    """The template's entry in the JSON report."""

    changed: bool
    date_last_updated: str
    etag: str


class PayloadJson(TypedDict):
    """The JSON report the tool emits with --json."""

    determined: bool
    problems: list[str]
    changed: bool
    baseline_captured: str | None
    template: TemplateJson | None
    languages: dict[str, LanguageJson]


REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHECK = REPO_ROOT / "dev" / "check_launchpad.py"

_ETAG = '"fixture-etag"'
_DATE = "2026-09-27T14:19:54.066364+00:00"

# A trimmed but verbatim rendering of the rows on the real series page
# (fetched 2026-10-10): the per-language anchors, the optional
# ?show=untranslated / ?show=new_suggestions links, and the <time> elements.
_PAGE = """<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Translations</title></head>
<body>
<table>
<tr class="stats language-af not-preferred-language">
  <td><a href="/scantpaper/trunk/+pots/scantpaper/af/+translate">Afrikaans</a></td>
  <td><span class="sortkey">000.00</span></td>
  <td>
    <span class="sortkey">549</span>
    <a href="/scantpaper/trunk/+pots/scantpaper/af/+translate?show=untranslated">549</a>
  </td>
  <td><span class="sortkey">0</span> 0</td>
  <td>
    <span class="sortkey">2026-09-27 15:24:49 UTC</span>
    <time title="2026-09-27 15:24:49 UTC" datetime="2026-09-27T15:24:49.094757+00:00">2026-09-27</time>
  </td>
</tr>
<tr class="stats language-de preferred-language">
  <td><a href="/scantpaper/trunk/+pots/scantpaper/de/+translate">German</a></td>
  <td><span class="sortkey">100.00</span></td>
  <td><span class="sortkey">0</span> 0</td>
  <td><span class="sortkey">0</span> 0</td>
  <td>
    <span class="sortkey">2026-09-27 14:13:16 UTC</span>
    <time title="2026-09-27 14:13:16 UTC" datetime="2026-09-27T14:13:16.839623+00:00">2026-09-27</time>
  </td>
</tr>
<tr class="stats language-it not-preferred-language">
  <td><a href="/scantpaper/trunk/+pots/scantpaper/it/+translate">Italian</a></td>
  <td><span class="sortkey">98.72</span></td>
  <td>
    <span class="sortkey">7</span>
    <a href="/scantpaper/trunk/+pots/scantpaper/it/+translate?show=untranslated">7</a>
  </td>
  <td>
    <span class="sortkey">14</span>
    <a href="/scantpaper/trunk/+pots/scantpaper/it/+translate?show=new_suggestions">14</a>
  </td>
  <td>
    <span class="sortkey">2026-09-27 16:07:54 UTC</span>
    <time title="2026-09-27 16:07:54 UTC" datetime="2026-09-27T16:07:54.872024+00:00">2026-09-27</time>
  </td>
</tr>
</table>
</body>
</html>
"""

_FR_ROW = """<tr class="stats language-fr not-preferred-language">
  <td><a href="/scantpaper/trunk/+pots/scantpaper/fr/+translate">French</a></td>
  <td><span class="sortkey">100.00</span></td>
  <td><span class="sortkey">0</span> 0</td>
  <td><span class="sortkey">0</span> 0</td>
  <td>
    <span class="sortkey">2026-09-27 15:00:00 UTC</span>
    <time title="2026-09-27 15:00:00 UTC" datetime="2026-09-27T15:00:00+00:00">2026-09-27</time>
  </td>
</tr>
</table>
"""

_PAGE_WITH_FR = _PAGE.replace("</table>", _FR_ROW)

_LANGUAGES = {
    "af": {
        "last_changed": "2026-09-27 15:24:49",
        "untranslated": 549,
        "suggestions": 0,
    },
    "de": {"last_changed": "2026-09-27 14:13:16", "untranslated": 0, "suggestions": 0},
    "it": {"last_changed": "2026-09-27 16:07:54", "untranslated": 7, "suggestions": 14},
}


def _api_text() -> str:
    """Return the template-resource JSON the tool consumes."""
    return json.dumps(
        {
            "message_count": 549,
            "language_count": 36,
            "date_last_updated": _DATE,
            "http_etag": _ETAG,
        }
    )


def _baseline(languages: dict[str, object] | None = None) -> dict[str, object]:
    """Return a baseline matching the page and API fixtures."""
    return {
        "series": "trunk",
        "pot": "scantpaper",
        "captured": "2026-09-27T16:10:00+00:00",
        "template": {"date_last_updated": _DATE, "etag": _ETAG},
        "languages": copy.deepcopy(_LANGUAGES) if languages is None else languages,
    }


def _run(
    tmp_path: Path,
    *flags: str,
    baseline: dict[str, object] | str | None = None,
    page: str | None = None,
    api: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run dev/check_launchpad.py over file:// fixtures in ``tmp_path``.

    ``baseline`` is written to po/launchpad-state.json-style file; ``None``
    writes the default matching baseline, a dict writes those contents, a raw
    string is written verbatim (for malformed files), and the sentinel string
    ``"keep"`` leaves whatever is already there untouched.
    """
    baseline_path = tmp_path / "launchpad-state.json"
    if baseline != "keep":
        to_write = _baseline() if baseline is None else baseline
        if isinstance(to_write, dict):
            baseline_path.write_text(json.dumps(to_write, indent=2), encoding="utf-8")
        else:
            baseline_path.write_text(to_write, encoding="utf-8")

    (tmp_path / "api.json").write_text(
        api if api is not None else _api_text(), encoding="utf-8"
    )
    (tmp_path / "page.html").write_text(
        page if page is not None else _PAGE, encoding="utf-8"
    )

    return subprocess.run(
        [
            sys.executable,
            str(CHECK),
            "--baseline",
            str(baseline_path),
            "--api-url",
            (tmp_path / "api.json").as_uri(),
            "--html-url",
            (tmp_path / "page.html").as_uri(),
            *flags,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _payload(result: subprocess.CompletedProcess[str]) -> PayloadJson:
    """Return the --json report as a typed dict."""
    return cast("PayloadJson", json.loads(result.stdout))


def test_unchanged_reports_no_changes(tmp_path: Path) -> None:
    """A run whose template and languages match the baseline reports nothing."""
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No Launchpad translation changes since" in result.stdout

    payload = _payload(_run(tmp_path, "--json"))
    assert payload["determined"] is True
    assert payload["changed"] is False
    assert payload["template"] is not None
    assert payload["template"]["changed"] is False
    assert all(lang["changed"] is False for lang in payload["languages"].values())


def test_template_change_is_reported(tmp_path: Path) -> None:
    """A moved template is reported as a change, exiting successfully."""
    baseline = _baseline()
    baseline["template"] = {"date_last_updated": _DATE, "etag": '"stale-etag"'}
    result = _run(tmp_path, "--json", baseline=baseline)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["changed"] is True
    assert payload["template"] is not None
    assert payload["template"]["changed"] is True
    assert payload["template"]["etag"] == _ETAG


def test_translation_change_is_reported_with_template_unchanged(tmp_path: Path) -> None:
    """A language that moved while the template did not is still reported."""
    baseline = _baseline()
    assert isinstance(baseline["languages"], dict)
    it = baseline["languages"]["it"]
    assert isinstance(it, dict)
    it["last_changed"] = "2026-09-27 12:00:00"
    result = _run(tmp_path, baseline=baseline)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "it (changed): 2026-09-27 16:07:54" in result.stdout

    payload = _payload(_run(tmp_path, "--json", baseline=baseline))
    assert payload["changed"] is True
    assert payload["template"] is not None
    assert payload["template"]["changed"] is False
    assert payload["languages"]["it"]["changed"] is True
    assert payload["languages"]["it"]["last_changed"] == "2026-09-27 16:07:54"


def test_new_language_is_reported(tmp_path: Path) -> None:
    """A locale absent from the baseline is reported as new."""
    result = _run(tmp_path, "--json", page=_PAGE_WITH_FR)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = _payload(result)
    assert payload["changed"] is True
    assert payload["languages"]["fr"]["new"] is True


def test_unparseable_page_is_not_determined(tmp_path: Path) -> None:
    """A page with no language rows is reported as not determined, non-zero."""
    result = _run(tmp_path, page="<html><body>broken</body></html>")
    assert result.returncode != 0
    assert "could not determine the languages" in result.stdout

    payload = _payload(
        _run(tmp_path, "--json", page="<html><body>broken</body></html>")
    )
    assert payload["determined"] is False
    assert payload["template"] is not None
    assert payload["languages"] == {}


def test_api_failure_still_reports_languages(tmp_path: Path) -> None:
    """An unreadable template does not hide the per-language result."""
    result = _run(tmp_path, "--json", api="not json")
    assert result.returncode != 0
    payload = _payload(result)
    assert payload["determined"] is False
    assert payload["problems"]
    assert set(payload["languages"]) == {"af", "de", "it"}


def test_fail_on_change_exit_codes(tmp_path: Path) -> None:
    """--fail-on-change is the only way a detected change fails the run."""
    baseline = _baseline()
    assert isinstance(baseline["languages"], dict)
    it = baseline["languages"]["it"]
    assert isinstance(it, dict)
    it["last_changed"] = "2026-09-27 12:00:00"
    assert _run(tmp_path, "--fail-on-change", baseline=baseline).returncode == 1
    assert _run(tmp_path, "--fail-on-change").returncode == 0


def test_update_advances_baseline_then_reports_unchanged(tmp_path: Path) -> None:
    """--update absorbs the current state; the next run is then quiet."""
    result = _run(tmp_path, "--update", baseline={})
    assert result.returncode == 0, result.stdout + result.stderr
    updated = json.loads(
        (tmp_path / "launchpad-state.json").read_text(encoding="utf-8")
    )
    assert updated["template"]["etag"] == _ETAG
    assert set(updated["languages"]) == {"af", "de", "it"}

    quiet = _run(tmp_path, "--json", baseline="keep")
    assert quiet.returncode == 0, quiet.stdout + quiet.stderr
    assert _payload(quiet)["changed"] is False


def test_update_refused_when_not_determined(tmp_path: Path) -> None:
    """A partial read can never silently advance the baseline."""
    baseline_path = tmp_path / "launchpad-state.json"
    baseline_path.write_text(json.dumps(_baseline(), indent=2), encoding="utf-8")
    before = baseline_path.read_text(encoding="utf-8")
    result = _run(
        tmp_path,
        "--update",
        baseline="keep",
        page="<html><body>broken</body></html>",
    )
    assert result.returncode == 1
    assert "refusing to update the baseline" in result.stdout
    assert baseline_path.read_text(encoding="utf-8") == before


def test_update_dry_run_writes_nothing(tmp_path: Path) -> None:
    """--dry-run reports without touching the baseline."""
    baseline_path = tmp_path / "launchpad-state.json"
    result = _run(tmp_path, "--update", "--dry-run", baseline={})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry run" in result.stdout
    assert baseline_path.read_text(encoding="utf-8") == "{}"


def test_malformed_baseline_fails(tmp_path: Path) -> None:
    """An unparsable baseline is a hard failure, not a silent reset."""
    result = _run(tmp_path, baseline="not json")
    assert result.returncode != 0
    assert "cannot read baseline" in result.stdout


def test_baseline_that_is_not_an_object_fails(tmp_path: Path) -> None:
    """A JSON baseline that is not an object is a hard failure."""
    result = _run(tmp_path, baseline="[1, 2]")
    assert result.returncode != 0
    assert "not a JSON object" in result.stdout


def test_saved_page_snippet_parses_italian(tmp_path: Path) -> None:
    """The saved page snippet yields Italian's real last-changed and counts."""
    result = _run(tmp_path, "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    it = _payload(result)["languages"]["it"]
    assert it["last_changed"] == "2026-09-27 16:07:54"
    assert it["untranslated"] == 7
    assert it["suggestions"] == 14
    de = _payload(result)["languages"]["de"]
    assert de["last_changed"] == "2026-09-27 14:13:16"
    assert de["untranslated"] == 0
    assert de["suggestions"] == 0
