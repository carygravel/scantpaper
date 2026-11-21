# Proposal

## Why

ruff and ty are already pinned, but independently and inconsistently: the four
pip-based jobs in `test.yml` install `ruff==0.16.7`, the jammy job still
installs `ruff==0.16.5`, and `.pre-commit-config.yaml` pins `v0.16.6`; ty is
pinned only inside `test.yml`. Nothing tells us when either tool publishes a
newer release, and nothing asks whether adopting it would still pass this
repository (`ruff check`, `ruff format --check .`, `ty check .`) or would
force configuration changes. The project already solved this exact problem
for the OpenSpec CLI (`watch-openspec-releases`); this change brings the same
pin-and-watch discipline to the lint and type-check tools.

## What Changes

- Introduce a single source of truth for the ruff and ty versions
  (`dev/lint-versions`), and make every CI job install from it instead of
  hard-coding versions. Retire the stale jammy pin and converge the
  pre-commit `rev` on the same version (or drop the pre-commit hook if it is
  no longer load-bearing).
- Add `dev/check_linters.py`, mirroring `dev/check_openspec.py`: read the
  pins, fetch the latest ruff/ty releases from PyPI, install the candidate
  tools in an isolated environment, and run the same validation commands CI
  runs, classifying each tool as up to date, safe to upgrade, or blocked. It
  also surfaces config-migration warnings (obsolete settings or rule names)
  that indicate adopting the release means editing `pyproject.toml`, not
  just bumping a pin. It is read-only with respect to the repository and
  emits JSON, Markdown, and a human summary.
- Add a scheduled workflow (or extend `openspec-check.yml`) that keeps one
  living, labelled issue reporting the pinned, installed and latest versions
  per tool and whether each update is safe or blocked, closing it once the
  pins catch up.
- Reconcile the documentation that describes ruff/ty as editor-time only:
  they are also CI gates in five jobs. Update the `pyproject.toml` comments,
  `AGENTS.md`, `CONTRIBUTING.md` and `README.md`.

There is no user-visible behaviour change; this is developer tooling and CI
infrastructure.

## Capabilities

### New Capabilities
- `linter-version`: version pinning in a single source, release awareness
  from PyPI, and update validation for the lint and type-check tools (ruff,
  ty) that CI and the Zed editor use. This mirrors the `openspec-cli-version`
  capability from `watch-openspec-releases`, which exists only as a delta and
  has not yet been synced to the main specs.

### Modified Capabilities
- (none)

## Impact

- CI/CD: `.github/workflows/test.yml` (install from the pin file), and
  `.github/workflows/openspec-check.yml` or a new `lint-check.yml` workflow.
- New developer tooling: `dev/lint-versions` and `dev/check_linters.py`,
  with its tests under `dev/tests/`.
- Configuration: `.pre-commit-config.yaml` (converged `rev` or removal), and
  the `pyproject.toml` comments describing ruff/ty as editor-time only.
- Docs: `AGENTS.md`, `CONTRIBUTING.md`, `README.md`.
- Dependencies: none for the runtime package; the check script stays
  standard-library-only like `dev/check_openspec.py`.
