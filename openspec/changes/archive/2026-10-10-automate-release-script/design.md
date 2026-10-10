## Context

See `proposal.md` for motivation. The relevant current state:

- A release is recorded in three tracked files. History shows every release
  commit touching exactly these three: `pyproject.toml`, `changelog.md`,
  `org.scantpaper.desktop.metainfo.xml`.
- `pyproject.toml` (`[project] version`) currently holds the *last released*
  version (3.0.21) while the newest `changelog.md` heading is the *next*
  version, `## 3.0.22 (unreleased)`.
- `changelog.md` uses `## X.Y.Z (YYYY-MM-DD)` headings, newest first.
- `org.scantpaper.desktop.metainfo.xml` lists releases newest-first inside
  `<releases>`, each as `<release version="X.Y.Z" date="YYYY-MM-DD" />`.
- `dev/` holds one-shot developer CLI scripts (`generate_pot.py`,
  `rosetta_tarball.py`, `check_po.py`) that use `argparse` and `print`, are not
  a Python package, and are exercised by tests via `subprocess`.

## Goals / Non-Goals

**Goals:**

- Make one command prepare the three files for release with a single, shared
  release date.
- Preserve the surrounding file formatting (comments, ordering, indentation)
  byte-for-byte outside the targeted edit.
- Fail safely: validate everything before writing anything.
- Be testable without touching the real repository files.

**Non-Goals:**

- No git operations (commit, tag, push).
- No `generate_pot.py`, no translation/tarball work.
- No changelog bullet authoring or `(unreleased)` section creation.
- No Debian/Ubuntu packaging steps.

## Decisions

### Decision: Python script at `dev/release.py`

Consistent with the other `dev/` tools and avoids adding code under
`src/scantpaper/`, where `--cov=scantpaper --cov-fail-under=99` would demand
coverage of developer tooling. Alternatives: a shell script (harder to unit
test and to preserve structured files) and a `src/scantpaper` module (drags
dev-only code into the shipped package and the coverage gate).

### Decision: Version derived from the changelog heading

The changelog's newest `(unreleased)` heading is the intended next version, so
it is the source of truth; `--version` is an assertion/override that MUST match.
This is self-validating and avoids a silent pyproject-vs-changelog divergence.
Alternative considered: bump `pyproject`'s patch component — rejected because it
cannot detect a mismatch and assumes the two are always in lockstep (they are
deliberately not, between releases).

### Decision: One resolved date, applied to both files

The changelog date and metainfo date are computed once and reused, which is the
core defect being fixed. Resolution order: `--date`, then `SOURCE_DATE_EPOCH`
(UTC), then the current local date. Alternative: derive each date independently
(rejected — reintroduces the drift).

### Decision: Targeted line edits, not full parse/serialize

The three files are read and written as text, changing only the specific line
(version line, heading, release entry). `tomllib` may be used to *read and
validate* the current version, but the file is not re-serialized, so comments,
key order and formatting survive. Likewise the metainfo entry is spliced after
the `<releases>` tag rather than round-tripped through an XML serializer, which
would reflow the file and drop the comment header. Alternatives: `tomlkit` /
`ElementTree` full rewrites — rejected for churn and a new dependency.

### Decision: All-or-nothing writes

Each transformation is a pure function `str -> str`; all three are computed and
validated in memory first, then written. A failure (missing heading, unparsable
metainfo, no `<releases>` element) aborts before any file is touched. This is
the substitute for the undo that git would otherwise provide.

### Decision: Testing via subprocess on a fixture tree

Follow the `test_po_files.py` pattern: build a throwaway directory with the
three files, run `dev/release.py --src <dir> --version ... --date ...`, and
assert on the resulting contents and exit codes. A `--src`/root option (default
the repo root) keeps the test off the real files. Unit-level coverage of the
pure helpers can be added by importing the module, but the black-box subprocess
tests are the primary contract.

## Risks / Trade-offs

- [Regex/line-anchored edits brittle to format changes] → Keep patterns narrow
  and anchored (`^version = "..."` in the `[project]` table region; `^##
  <version> (unreleased)$`; the `<releases>` opening tag), and validate the
  result (e.g. the version now parses, the heading is gone, the new entry
  exists) before writing.
- [Multiple or missing `(unreleased)` headings] → Require exactly one match;
  otherwise abort with a clear message.
- [Date timezone surprises] → Default to the local calendar date (what a
  maintainer expects to type); `SOURCE_DATE_EPOCH` is interpreted as UTC. The
  chosen value is printed so it can be overridden with `--date`.
- [`changelog.md` is also user-facing documentation] → The edit is limited to
  one date token, leaving bullets and surrounding sections untouched.

## Open Questions

None.
