## Why

The release procedure's first step is "Download new translations
(https://translations.launchpad.net/scantpaper)". Nothing tells the maintainer
*when* there is anything to download: between releases a translator can confirm
dozens of strings, and an unreviewed suggestion can sit indefinitely, with no
signal anywhere in the repository. The receiving side is already automated
(`dev/check_po.py`, `dev/summarise_po.py`, `dev/rosetta_tarball.py`); the
detecting side has none.

The upstream state is fully readable without authenticating, so the signal is
obtainable — it is simply never consulted. As measured on 2026-10-10, the
template carries 549 messages across 36 languages, and Italian alone shows 14
unreviewed suggestions and 7 untranslated strings. None of that is visible from
the working tree.

The event we care about is a *change*, not a snapshot: "has anything moved on
Launchpad since we last pulled the catalogs?" Answering it means comparing each
unit of upstream state — the template, and each language — against what it was
the last time the catalogs were pulled. That reference point does not exist
today, so nothing can detect the movement.

## What Changes

- Add `dev/check_launchpad.py`, which compares the current public Launchpad
  state against a committed baseline (`po/launchpad-state.json`) and reports
  what changed. It watches two independent triggers, each read from the only
  source that carries it:
  - the **template** (the message set / `.pot`), from the public JSON API
    resource for the translation template, using its `date_last_updated` and
    entity tag (`If-None-Match`, so an unchanged template costs a `304`);
  - **per-language translation activity**, from the public series translation
    page, whose per-language last-changed timestamps and counts exist nowhere
    else.
- The baseline is a **sampled snapshot of what Launchpad reported** at the last
  sync, not something derived from git. It is advanced only by an explicit
  `--update` run after the catalogs have been pulled. (Git is not usable as the
  anchor; see the design.)
- The tool **never downloads catalogs**. Every Launchpad `+export` endpoint
  requires login, so the actual sync stays the manual release-procedure step.
- The check is **advisory**: it exits successfully whether or not a change is
  found, and never gates a release. CI can opt into failing on change with an
  explicit flag. The one non-zero default is a check that genuinely could not
  run.
- Add a **scheduled GitHub workflow** that runs the check weekly and opens or
  updates a single labelled issue when upstream has moved.
- Add **no dependencies**: the tool uses only the standard library
  (`urllib.request`, `json`, `html.parser`, `argparse`).
- Document the check in `release_procedure.md`, `README.md` and `AGENTS.md`.

## Capabilities

### New Capabilities

<!-- None. This change extends the existing `translations` capability. -->

### Modified Capabilities

- `translations`: adds a requirement that the public Launchpad state of the
  translation template and of each language is compared against a committed
  snapshot without authenticating, that the languages whose timestamps moved are
  reported, and that no catalog is downloaded (which Launchpad gates behind a
  login).

## Impact

- New file: `dev/check_launchpad.py`.
- New baseline: `po/launchpad-state.json` (committed).
- New test: `src/scantpaper/tests/test_launchpad.py`.
- New workflow: `.github/workflows/translations-check.yml`.
- Modified docs: `release_procedure.md`, `README.md`, `AGENTS.md`.
- No runtime or application code changes, no new dependencies, no packaging
  changes.

### Scope boundary worth stating

The obvious next question is "why not download the catalogs too?" The answer is
that Launchpad does not expose them anonymously: every `+export` variant
(`/trunk/+export`, per-language `/<lang>/+export`, and the per-pot form) answers
an unauthenticated request with `303 → +login`, and the JSON API offers no
operation that returns catalog content. Only the *state* is public. This change
deliberately stops at the state, so it automates what can be automated safely
and leaves the authenticated fetch as the one manual step it already is.
