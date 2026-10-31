# Design

## Context

See `proposal.md` - Why. Constraints that shape the approach:

- The tools live in `dev/` upstream and run in a salsa checkout after
  `gbp import-orig`, where the working tree already holds the new upstream
  `packaging/` tree next to `debian/`.
- `dev/` is not a Python package, so the two tools are siblings with a small
  amount of duplicated plumbing, as `prepare_rpm.py` and `prepare_deb.py`
  already are.
- The salsa repository keeps `debian/changelog` as its only owned file once
  the patches are deleted and `clean` moves upstream.
- `dch` always opens an editor for the entry text, so it cannot produce a
  deterministic draft. The tools write the entry directly in the same format.
- gbp exports the orig tarball from pristine-tar; Launchpad rejects a
  different orig for an upstream version it has already seen.
- The four `ubuntu:<series>` container images are pullable, so the matrix can
  be checked against the real archive.

## Goals / Non-Goals

**Goals:**

- Make a release sync a copy plus one reviewed changelog entry, with drift
  caught instead of silently preserved.
- Generate each Ubuntu source package from the same packaging with only the
  series-specific differences applied.
- Keep signing and both uploads deliberate.

**Non-Goals:**

- Automating `gbp import-orig`, commits, tags, pushes, `debsign` or `dput`.
- Managing per-series branches, Launchpad recipes or PPA dependencies.
- Changing the GitHub `.deb` build or its version scheme.
- Sanitising the packaged README; only the generated HTML is stripped.

## Decisions

### Decision: two sibling scripts, no shared module

`dev/sync_salsa.py` and `dev/build_ppa.py`. They share only tiny helpers
(reading `pyproject.toml`, running git), and importing across `dev/` would
need a package or `sys.path` manipulation. Keeping them separate follows the
existing renderer pair and keeps each testable on its own.

### Decision: the copy is exact and leftover files fail

The shared set is every file in `packaging/debian/` except `README.md` and the
`changelog` template. The tool copies that set into `debian/`, deletes shared
files no longer present upstream, and then requires the only remaining
non-shared file to be `debian/changelog`. Anything else - a patch series, a
leftover install file - fails the run with its name.

This turns the one-off patch deletion into an enforced invariant instead of a
convention, and it is what makes "copy plus a changelog" true rather than
aspirational.

### Decision: identity fields move upstream

`packaging/debian/control` adopts salsa's `Maintainer`, `Uploaders`,
`Vcs-Git` and `Vcs-Browser`. The two files become identical, so the copy needs
no merge rule. The GitHub `.deb` then reports the Debian Python Team as
maintainer; `Uploaders` and `Vcs-*` are source-only fields, so the binary
package is otherwise unchanged.

Alternatives rejected: a protected-field merge (a rule that exists only to
keep two files almost equal) and placeholders (a second templating mechanism
in a file that does not need one).

### Decision: the changelog entry is written directly, dated midnight UTC

The tool inserts:

```text
scantpaper (<upstream>-<revision>) unstable; urgency=medium

  * New upstream release.
    <classified bullets>

 -- <packager>  <date>
```

- `<upstream>` comes from `pyproject.toml` in the imported tree.
- `<revision>` is `1` when the upstream version differs from the newest entry
  and one higher when it matches.
- The packager line is reused from the newest existing trailer.
- The date defaults to today at `00:00:00 +0000`, matching the existing
  entries, and can be overridden with `--date` or `SOURCE_DATE_EPOCH`.

The diff baseline is the previous release, read from the newest `debian/*`
tag rather than `HEAD`: after `gbp import-orig`, `HEAD` already contains the
new upstream tree, and only the tag still holds the packaging as it was
released. Using the tag also makes a re-run replace the draft instead of
bumping the revision again.

The first release after the packaging moved upstream has no baseline: the
previous tag predates `packaging/debian`. In that case the tool requires
`debian/` to hold only the changelog, copies the tree, and drafts no diff
bullets; the one-off cleanup is documented in the release procedure.

### Decision: classify the diff, do not summarise it

Bullets are generated deterministically:

- added shared files: `debian/tests/control: new`
- removed shared files: `debian/scantpaper.install: removed`
- `control`: added/removed package names in `Build-Depends`,
  `Build-Depends-Indep`, `Depends` and `Recommends`
- `rules`: `debian/rules: updated`
- anything else: `debian/<path>: updated`

The tool writes facts it can prove and leaves the wording to the maintainer.
It never claims a reason it cannot derive from the diff.

### Decision: the PPA matrix has two knobs

`packaging/ubuntu/suites.toml`:

```toml
[series.stonking]
debhelper-compat = 14

[series.resolute]
debhelper-compat = 13

[series.noble]
debhelper-compat = 13

[series.jammy]
debhelper-compat = 13
drop-test-depends = ["jbig2"]
```

Those are the only differences found: compat, which follows the archive, and a
test dependency a series does not carry. Everything else is the Debian tree.
The file rides in the upstream tree, so the copy stays clean.

### Decision: build each series from the committed branch

The PPA step runs after the sync is committed, so it extracts the branch
with `git archive` rather than copying a dirty tree. That keeps untracked
build output out of the source package and leaves the salsa working tree
untouched. Uncommitted changes under `debian/` or `packaging/` are refused;
untracked build output such as `debian/files` is ignored.

For each series the tool:

1. applies the changelog rewrite (version and `Distribution`), the
   `debhelper-compat` substitution, and any `drop-test-depends` edits;
2. obtains the orig tarball with `gbp export-orig --pristine-tar` and reuses
   that file;
3. runs `debuild -S -us -uc -sa` into `build/ppa/<series>/`;
4. prints `debsign` and `dput` and removes the tree.

Source packages are unsigned on purpose; signing is the maintainer's step.

### Decision: matrix verification is a container query

With `--verify`, the tool runs `apt-cache show debhelper` in
`ubuntu:<series>` (podman or docker) and checks that the configured compat is
in its `Provides`. A stale matrix fails before anything is built, with the
series named. The mode is off by default so routine builds need no container
runtime.

### Decision: version and import preconditions are explicit

Both tools require `debian/changelog`, `packaging/debian/` and a git worktree,
and the sync additionally requires the branch named by `--debian-branch`
(default `debian/master`) and an `upstream/<version>` tag matching
`pyproject.toml`. Missing preconditions fail before any file is written, with
the missing piece named.

### Decision: tests use throwaway repositories

The sync tests build a small git repo with a `debian/` tree, a
`packaging/debian/` tree and a changelog, then run the tool as a subprocess,
as the renderer tests already do. They cover the copy, deletion, leftover
failure, revision logic, date override and each bullet class. The PPA tests
apply the matrix to a copy of the tree and inspect the generated changelog,
control and test control; the actual source build is exercised once in the
integration check rather than per test.

## Risks / Trade-offs

- [The changelog bullets are heuristic] -> They state only verifiable facts
  and are left editable; the maintainer still signs the entry by committing.
- [The leftover check can block a legitimate salsa-only file] -> Add the file
  upstream if it is shared, or extend the owned set deliberately; the failure
  names it.
- [A series' compat changes after the matrix was written] -> `--verify`
  catches it against the real archive; the static matrix stays the default to
  avoid a container dependency on every run.
- [The orig tarball can differ from what Launchpad already has] -> Always
  export it from pristine-tar and reuse that file.
- [The PPA step needs a committed sync] -> Refuse a dirty tree with a clear
  message; the release procedure already commits before the Ubuntu step.
- [The team identity appears on the GitHub artifact] -> Accepted; the
  packaging is the Debian packaging and the fields are source-only.
- [Two scripts duplicate a little plumbing] -> Accepted, as with the two
  renderers; sharing would need `dev/` to become a package.

## Migration Plan

1. Unify the packaging: control identity, `clean` upstream, delete the two
   patches and the series in salsa.
2. Add the matrix and the sync tool with tests; run it on a scratch salsa
   clone and compare the result.
3. Add the PPA tool; build a noble source package without uploading it.
4. Update the procedure and changelog; run the full quality gates.
5. Use the tools on the next release. Rollback is a revert; the salsa
   repository keeps its history and no upload is undone.

## Open Questions

- Should `--verify` run automatically in the release procedure? Deferred until
  a matrix value has actually gone stale.
- Should the Ubuntu images be pinned by digest? Deferred; `ubuntu:<series>` is
  only used by `--verify`.
