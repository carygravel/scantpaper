## 1. Baseline format and script skeleton

- [x] 1.1 Define the committed baseline `po/launchpad-state.json`: top-level
  `series`, `pot`, `captured`, a `template` object
  (`date_last_updated`, `etag`), and a `languages` object mapping each language
  code to `{last_changed, untranslated, suggestions}`
- [x] 1.2 Add `dev/check_launchpad.py` with a module docstring describing the
  two triggers, the read-only advisory contract, and the sampled-snapshot
  baseline, following the `argparse`/`print` style of `dev/release.py`
- [x] 1.3 Add state load/save helpers that read and write the baseline as UTF-8
  JSON and fail with a clear message on a malformed file
- [x] 1.4 Capture an initial `po/launchpad-state.json` from the live API and
  HTML page and commit it

## 2. Template trigger (API)

- [x] 2.1 Add an URL-overridable fetch helper (`--api-url`, default the live
  template resource) that sends a descriptive `User-Agent` and an
  `If-None-Match` header carrying the baseline entity tag
- [x] 2.2 Treat `304 Not Modified` as no template change without reading a
  body, and treat a changed `http_etag` or `date_last_updated` as a change
- [x] 2.3 Make a missing or unexpected field raise "could not determine" for
  the template part rather than silently reporting "unchanged"

## 3. Per-language trigger (HTML)

- [x] 3.1 Add an URL-overridable fetch helper for the series translation page
  (`--html-url`), fetched on every run
- [x] 3.2 Add an `html.parser.HTMLParser` subclass that extracts one record per
  language — `last_changed`, `untranslated`, `suggestions` — keyed on the
  per-language `…/<lang>/+translate` link and the optional
  `?show=untranslated` / `?show=new_suggestions` links, not on presentational
  class names
- [x] 3.3 Treat a page that cannot be parsed, or that yields no language
  records, as "could not determine" for the translation part — never as
  "unchanged" — while still reporting the template part

## 4. Compare and report

- [x] 4.1 Compare each unit against the baseline: the template by
  `http_etag`/`date_last_updated`, each language by `last_changed`, and report a
  language present live but absent from the baseline as a new locale
- [x] 4.2 Print a human-readable report: unchanged, or the changed units with
  their new untranslated/suggestion counts, or the not-determined note
- [x] 4.3 Add `--json` emitting the same result for the workflow to consume
- [x] 4.4 Exit codes: `0` for unchanged or changed, non-zero only for
  "could not determine"; `--fail-on-change` makes a detected change non-zero

## 5. Baseline update and CLI

- [x] 5.1 Add `--update` that absorbs the current state into the baseline,
  computing all changes before writing (all-or-nothing) and honouring
  `--dry-run`
- [x] 5.2 Refuse to `--update` from a "could not determine" run, so a partial
  read can never silently advance the baseline
- [x] 5.3 Confirm a run issues exactly one API request and one page request,
  sends no credentials, and sends no request to any `+export` endpoint

## 6. Scheduled workflow

- [x] 6.1 Add `.github/workflows/translations-check.yml` with a weekly `cron`
  and `workflow_dispatch`, running `python3 dev/check_launchpad.py --json`
- [x] 6.2 On a detected change, create or update the single open issue carrying
  a dedicated label, using the tool's report as the body; on no change, do
  nothing; on "could not determine", let the job fail
- [x] 6.3 Confirm the workflow requests only `contents: read` and
  `issues: write`

## 7. Documentation

- [x] 7.1 Add a step to `release_procedure.md` noting that the check reports
  upstream changes and that the baseline is advanced with `--update` after the
  catalog sync
- [x] 7.2 Document the check and the baseline in the Translations section of
  `README.md`
- [x] 7.3 Note the check in the translations workflow section of `AGENTS.md`
  alongside the catalog-validation steps

## 8. Tests

- [x] 8.1 Add `src/scantpaper/tests/test_launchpad.py` driving the script as a
  subprocess over `file://` fixtures, matching `test_release.py`
- [x] 8.2 Cover: unchanged; template changed with a parseable page; a
  translation changed (page only) with the template unchanged; a page that will
  not parse; and a template read that cannot be determined
- [x] 8.3 Cover `--fail-on-change` exit codes for changed and unchanged
- [x] 8.4 Cover `--update` advancing the baseline, a following run reporting
  unchanged, `--update` refusing a not-determined run, and `--dry-run` leaving
  the baseline untouched
- [x] 8.5 Add a parser test against a saved snippet of the real translation
  page, asserting a language's `last_changed`, `untranslated` and `suggestions`

## 9. Verification

- [x] 9.1 `python3 -m pytest -q` — all pass, coverage not below the configured
  threshold, and no test reaches the network
- [x] 9.2 `ruff check` and `ruff format --check` clean on all touched files
- [x] 9.3 `ty check .` clean
- [x] 9.4 A manual run against the live endpoints reports correctly and makes
  exactly two requests
