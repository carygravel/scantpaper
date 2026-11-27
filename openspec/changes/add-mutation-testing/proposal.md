# Proposal

## Why

The application suite already enforces 99% branch coverage, but coverage only
proves that a line executed; it does not prove that a test would fail if that
line were wrong. Mutation testing closes that gap by injecting small semantic
changes and checking whether the suite notices. A pilot on
`src/scantpaper/savethread.py` found surviving mutants in the progress-bar
fraction and in `SaveThreadProgressBar.__exit__`, where returning `True`
would silently suppress an exception raised during a save. Those are
user-facing failure modes that the current gates cannot see.

The check is for developer machines and CI only. It must never run against a
user installation and must not add a runtime dependency to the application.

## What Changes

- Add a pinned, developer-only mutation-testing environment using
  `pytest-gremlins`. The tool is installed from a recorded pin, not from the
  shipping dependencies or the `[test]` extra.
- Mutate only the shipped `scantpaper` package. The `dev/` tooling is
  explicitly out of scope.
- Add a curated target manifest and a thin runner under `dev/` that selects
  the targets, neutralises the normal coverage gate for the mutation run, and
  emits a machine-readable report separating killed, survived, no-test,
  error, and timeout outcomes.
- Add a scheduled advisory workflow that runs the curated targets, uploads
  the JSON and HTML reports, records a run summary, and files or updates one
  issue. It does not gate pull requests, and it exits non-zero only when the
  run itself cannot be completed.
- Document the local command, the target-tier policy, and the equivalent-
  mutant policy. Survivors are triaged with the tool's inline pardon syntax;
  blanket exclusions are not permitted.
- Ignore the tool's cache and report directories in `.gitignore`.

Report-only adoption is deliberate. A per-target ratchet is a follow-up once
the score is shown to be stable across the supported developer and CI
environments.

## Capabilities

### New Capabilities

- `mutation-testing`: defines which code is mutated, how a run classifies
  each mutant, how survivors are triaged, and how the scheduled advisory
  report is produced.

### Modified Capabilities

None. No application behaviour, command-line interface, output file, or
packaging contract changes.

## Impact

- Affected code: a new `dev/` runner and target manifest; a new scheduled
  workflow; `.gitignore`; developer documentation.
- Dependencies: one development-only tool pin. No runtime or package
  dependency changes.
- CI: one additional scheduled job on `ubuntu-latest`. The normal push test
  matrix and the coverage gate are unchanged.
- Platforms: the runner requires Python 3.11 or newer, so it runs on the
  current noble and Debian testing developer machines and on the CI runner.
  It is not installed on the Python 3.10 jammy test job.
