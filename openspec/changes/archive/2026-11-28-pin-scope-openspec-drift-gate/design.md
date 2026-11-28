# Design

## Context

See `proposal.md` - Why. The facts that shape the approach, measured on this
tree:

- `dev/check_generated_instructions.py` runs `openspec update --dry-run
  --json`, keeps the planned changes whose path resolves inside `--root`, and
  exits 1 when any remain. It never reads `dev/openspec-version`; the CLI it
  runs is whatever `PATH` resolves.
- The CLI prints the global configuration as `~/.config/openspec/config.json`
  when `XDG_CONFIG_HOME` is unset, and as an absolute path when it is set. A
  clean `HOME` therefore produces one planned change that a configured
  developer home does not.
- This machine has 2.0.0 installed against a 2.2.0 pin: the dry run plans six
  `.agents` rewrites and twelve deletions of untracked `.opencode` files. The
  same run with 2.2.0 on CI plans only the home configuration.
- `dev/check_openspec.py` installs `@latest` in the scheduled job and runs
  `DEFAULT_VALIDATE_COMMANDS`, which currently includes the gate. Its issue
  body says "Do not bump the pin yet" for a blocked candidate.

## Goals / Non-Goals

**Goals:**

- One question per check: the gate answers "does the tree match the pinned
  CLI"; the scheduled check answers "does the candidate's own validation
  pass".
- A clean runner is green, and a developer with the wrong CLI gets a truthful
  "cannot judge" rather than a stale verdict.
- The scheduled check cannot report a pin-relative drift as a candidate
  failure, so a bump is never blocked by the refresh it is about to perform.

**Non-Goals:**

- Installing the pinned CLI from the gate, or making it network-dependent.
- Isolating the CLI's global configuration (a temporary `HOME` or
  `XDG_CONFIG_HOME`) to make the plan independent of the developer's
  preferences. The containment filter already ignores that entry once it is
  resolved correctly.
- Tracking or ignoring the untracked `.opencode` leftovers; `openspec update`
  under the pin removes them.
- Changing the pin, the installed CLI, or the CI install step.
- A `README.md` entry; this is developer tooling, so no user-visible
  behaviour changes.

## Decisions

### D1 - Expand `~` before the containment check

`Path(change.path).expanduser()` runs before the absolute/relative branch, so
a home-relative path is compared as an absolute path outside the repository.
`Path.resolve()` alone does not expand `~`; that is the defect.

- Alternative: skip any path beginning with `~`. Rejected - it would also skip
  a home that genuinely contains the repository, and it hides the mistake
  instead of modelling the CLI's notation.
- Alternative: run the CLI with a temporary `XDG_CONFIG_HOME`. Rejected - it
  changes the plan (the config add is always present), couples the gate to one
  variable, and the entry still has to be filtered.
- Alternative: reject any path that is not absolute or repo-relative. Rejected
  - relative paths are genuinely repo-relative, and the gate must keep
  accepting them.

`expanduser()` uses `HOME` on POSIX, the same source the CLI uses, so the
reconstruction matches on every platform this repository supports.

### D2 - The gate reads the pin and compares the CLI it runs

Add a `--pin-file` option, defaulting to `dev/openspec-version` under
`--root`. The gate reads the pin, runs `<cli> --version`, and compares the
stripped strings. On a mismatch it reports a distinct state, exits 2, and
names the installed and pinned versions plus the install command. It does not
report the files as current or stale, because it has not looked at a plan it
can attribute to the pin.

- Exit 2 already means "cannot tell" in this script, so the new outcome joins
  the existing "CLI missing, output unreadable, plan failed" cases.
- The version is the exact npm release and the CLI prints it verbatim, so a
  string comparison is enough. An unexpected value is reported as-is rather
  than parsed, which keeps one version parser (`check_openspec.parse_version`)
  rather than two.
- Alternative: run the pin through `npx @fission-ai/openspec@<pin>`.
  Rejected - it needs the network at gate time, and CI has already installed
  the pin.
- Alternative: skip the check when the pin file is missing. Rejected - this
  repository always has a pin, so a missing pin is a cannot-tell, not a pass.

### D3 - The drift gate is an adoption verification, not a candidate validation

`DEFAULT_VALIDATE_COMMANDS` loses the gate; `ADOPT_COMMANDS` gains it after
`openspec update`. The rendered issue body becomes: write the pin, install the
release, refresh the instruction files, verify the refresh, then run the
validation commands CI runs. `test.yml` keeps its step unchanged.

A candidate cannot satisfy a property that is defined against the pin. Keeping
the gate in the candidate list makes every file-changing release "blocked",
and the blocked text tells the maintainer not to bump until the gate passes -
which only the bump can do.

- Alternative: keep the gate in the candidate list and let a version mismatch
  pass there. Rejected - the command would always pass under a candidate, so
  it would report a meaningless "ok" and still not verify the refresh.
- Alternative: add a `--allow-other-version` flag for the scheduled check.
  Rejected - the same command would mean two things, and both modes need
  tests.

### D4 - One report shape, three states

The JSON report gains an `unchecked` state for the version mismatch, with an
empty `changes` list and a summary naming both versions. The human summary
keeps its existing wording for `current` and `stale` and uses the same
`[FAIL]`-free format for `unchecked`, so a reader sees an environment problem,
not a repository defect.

### D5 - Tests own their environment

The stub CLI answers `--version` as well as `update`, so no test depends on the
real CLI. The tilde test runs the gate with `HOME` set to a temporary
directory, so it does not depend on the developer's configuration. The
`check_openspec` tests assert the new placement: the gate is absent from
`DEFAULT_VALIDATE_COMMANDS`, present in `ADOPT_COMMANDS`, and ordered after
the refresh in the issue body.

## Risks / Trade-offs

- [A developer with a CLI that differs from the pin now gets exit 2] ->
  Intentional: the message names both versions and the install command, which
  is the documented setup step.
- [The scheduled check no longer exercises the gate against a candidate] ->
  The property is unverifiable before adoption; the adoption block verifies it
  immediately after the refresh, and `test.yml` gates every push.
- [The gate still measures the working tree, so untracked generated files
  count as drift] -> Accepted; CI checks a clean checkout, and the local
  remedy removes them. Making the gate git-aware would add a second source of
  truth.
- [A future CLI could print a different home notation] -> The home-relative
  test covers `~`; `expanduser()` also handles `~user`. Any other notation is
  a new case with its own test, not a silent pass.

## Migration Plan

1. Land the path fix and its tests as the first commit; CI goes green with the
   pin already installed there.
2. Land the pin comparison, the command move, the spec delta and the
   `AGENTS.md` wording as the rest of the change.
3. Rollback is a revert: the gate returns to `PATH`-scoped behaviour and the
   scheduled check to replaying it. No data or configuration migrates.
