# Proposal

## Why

`test.yml` pins the OpenSpec CLI so an upstream rule change cannot turn the
build red without a deliberate bump, but nothing reports when a newer release
exists or whether this repository passes it. The pin was still 1.14.3 while
npm had published 1.16.0, and the failure mode is invisible until someone
bumps: 1.14.3 added a "requirement text is very long" warning that `--strict`
turns into an error, which reddened CI only after the fact.

Deciding to bump therefore costs a manual `npm view` lookup, a throwaway
`npx … validate`, and the risk of finding out at push time. That check is
forgotten, so the pin drifts.

## What Changes

- Record the pinned version in a one-line file, `dev/openspec-version`, and
  install from it in `test.yml` instead of hard-coding the version twice.
- Add `dev/check_openspec.py`, which reads the pin, asks the npm registry for
  the `latest` release, runs the candidate CLI's validation commands, and
  reports one of three states: current, safe to upgrade, or blocked.
- Add `.github/workflows/openspec-check.yml`, scheduled daily, which installs
  the candidate CLI, runs the check, and files a single living issue whose
  title says either "safe to upgrade" or "blocked by" the failing command.
  When the pin catches up the issue is closed automatically.
- Bump the pin from 1.14.3 to 1.16.0, which both validation commands accept
  today.
- Document the workflow and the bump procedure in `AGENTS.md`.

## Capabilities

### New Capabilities

- `openspec-cli-version`: how the pinned OpenSpec CLI version is recorded, how
  a newer release is detected and validated against this repository, and how
  that state is reported to the maintainer.

### Modified Capabilities

None: no runtime behaviour and no existing requirement changes.

## Impact

- `.github/workflows/test.yml` installs from `dev/openspec-version`.
- `.github/workflows/openspec-check.yml` (new) needs `contents: read` and
  `issues: write`, and one label, `openspec-update`.
- `dev/openspec-version` (new), `dev/check_openspec.py` (new) and
  `dev/tests/test_openspec.py` (new). Standard library only, so no new Python
  dependency.
- `AGENTS.md` gains the workflow description and replaces the three manual
  npm commands with the automated report plus the one-line bump.
- No application code, packaging, or translations are touched.
