# Design

## Context

See `proposal.md` for motivation and the delta spec for the required
behavior. Today `dev/build_ppa.py` prints the next steps inside
`_build_series`, once per series. `_build` raises `PpaError` on failure,
which unwinds through `build` to `main`; `main` prints the error on stderr
and returns 1. Any commands for series that finished earlier have already
been printed by the time the failure occurs.

## Goals / Non-Goals

**Goals:**

- One `Next steps:` block in selection order after the loop.
- Keep the commands of series that finished before a later failure.
- Keep the existing exit status, signing, and progress lines.

**Non-Goals:**

- Continuing with later series after a failure.
- Changing the suite matrix, packaging files, or upload steps.
- Sharing a next-steps helper with `dev/sync_salsa.py`.

## Decisions

### Collect paths in `build`, print in `finally`

`_build_series` returns the `.changes` path instead of printing it.
`build` accumulates the paths and prints them in a `finally` around the
series loop, guarded by a non-empty check. This preserves the current
observable behavior on a mid-run failure: series that finished stay visible,
the failing series was never added, and `PpaError` still reaches `main` for
the non-zero exit.

Alternatives: a plain print after the loop was rejected because it would
hide commands that are visible today and force a rebuild; continuing past a
failure was rejected as a scope change that could produce packages from a
broken matrix.

### One header in every case

Use the same `Next steps:` header for a full run and a partial one. The
error is already on stderr and the exit status is non-zero, so a second
header variant such as "for the series built so far" adds a message branch
without adding information.

### Selection order, no per-line labels

Print in the order the series were selected: matrix order for `--all`, the
given order for repeated `--series`. Do not sort or group by series name.
The `.changes` path already names the series, so no extra label is needed.

### Dry run reuses the same path

`_build_series` returns the actual `.changes` path after a build and the
predicted `scantpaper_<version>_source.changes` path in `--dry-run`. Both
flows hand the same `list[Path]` to the printer.

### Keep the helper local and small

`_print_commands` takes the collected paths and the target, prints the
header once, then one `dput` line per path. Its name stays as it is, and
`dev/sync_salsa.py` keeps its own helper: the two print different command
sets and sharing would add coupling for no gain.

## Risks / Trade-offs

- **Partial output could look uploadable after a failure** -> the failing
  series is never listed, the error stays on stderr, and the process exits
  non-zero; the listed packages are the ones that did finish.
- **A series is only collected after `_build_series` returns** -> a failure
  in collecting or discarding the tree after the build omits that series.
  This is an exceptional path that is already visible as an error; adding
  state updates before the return is not worth the complexity.
- **`finally` also runs for unexpected exceptions** -> any series that
  finished before a crash keeps its command. That is the intended failure
  behavior, not a leak.

## Testing

Subprocess tests in `dev/tests/test_build_ppa.py` stay the pattern: a fake
`debuild` writes the `.changes` file the tool expects. New cases cover one
header across two series, selection order, a failure on the second series
(earlier command printed, failing series absent, exit non-zero), and a
failure on the first series (no header). The existing single-series build
and dry-run assertions remain valid.
