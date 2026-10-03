## Context

Three properties of the current openSUSE packaging make the published
artifact set uninstallable, and one property of the CI makes all three
invisible until a user reports them:

- The nine dependency specs are `Name: python3-*`. On Leap 16 that name is
  not a package name at all - `python313-foo` is the package and
  `python3-foo` is only a provide that repo-oss packages add alongside
  it. `packaging/opensuse/build.sh` derives the RPM filename globs from
  the same strings (`spec_for`, `rpmname_for`), so the mistake is
  duplicated across the specs, the build driver and the workflow.
- No spec writes `Requires: python3dist(...)`, and no spec ever did.
  `python-rpm-macros` pulls in `python-rpm-packaging`, whose
  `/usr/lib/rpm/fileattrs/pythondist.attr` defines `%__pythondist_provides`
  and `%__pythondist_requires`; Leap 16's copy has the requires line
  commented out (`#disabled for now`) while leaving the provides line
  active. Neither half is actually reached here: the generator matches a
  flat `<name>.dist-info` file, which a PEP 427 wheel does not produce (see
  D2), so these specs emit no `python3dist()` metadata of either kind. The
  name namespace below was the real defect; this is recorded because it is
  the trap the naming fix could easily have walked into.
- `python313-sane` is the one package we rebuild that repo-oss also
  ships (2.9.2, unpatched). The vendored PR-109 patch fixes a real
  `snap()` failure on backends such as Epson's `epsonscan2`, so the
  rebuild is wanted - but it means our `python313-sane` deliberately
  supersedes the distro's build of the same version.

Every `Verify` step in `.github/workflows/opensuse.yml` executes in the
build container immediately after `do_install` put our own RPMs on that
same system. Each dependency is therefore satisfied by a package we built
in the same job, so the check can only ever confirm internal consistency.

## Goals / Non-Goals

**Goals:**

- The published runtime set installs in one non-interactive transaction on
  a machine that has none of our packages on it.
- Installing it over an equivalent package from repo-oss or a third-party
  OBS repo performs a normal package replacement, never a file conflict.
- No built RPM carries a `python3dist()` require, and CI fails if one ever
  reappears.
- CI proves the above on every run, without a user having to report a
  broken install.

**Non-Goals:**

- Changing any application source, test, or runtime behaviour.
- Changing the Fedora packaging tree, which is correct for Fedora.
- Publishing to OBS, or otherwise making these RPMs installable by name
  from a repository. They remain unsigned release assets installed by
  path.
- Upstreaming the PR-109 patch to python-sane.

## Decisions

### D1. Name the packages `python313-<pypi-project-name>`

Each spec's `Name:` becomes the Leap 16 package name for the same PyPI
distribution, and `build.sh`'s `spec_for`/`rpmname_for` mappings move in
step. Note that the distribution name, not the import name, is what
openSUSE derives the package name from - so `python-iso639` becomes
`python313-python-iso639` (matching what `devel:languages:python` already
publishes) and `pdfminer.six` becomes `python313-pdfminer.six`.

Rationale: same-name is what makes rpm treat this as a replacement. With
`python3-iso639` and `python313-python-iso639` both owning
`site-packages/iso639/`, rpm has two unrelated packages claiming one file
and must prompt. With one name there is a single owner at every point in
time, so `rpm -V` stays coherent and a later `zypper update` of the
third-party package cannot silently restore stale files underneath us.

Alternative considered: keep `python3-*` and add
`Obsoletes: python313-python-iso639`. Rejected - it fights the
distribution's own naming policy, needs the obsoleted version tracked by
hand, and still leaves the wrong name in the published artifact.

### D2. Declare dependencies concretely; do not suppress the generator

Every Python spec declares its dependencies by concrete `python313-*` package
name, and no spec touches the pythondist dependency generator at all - no
suppression macro, no hand-written `python3dist()` metadata. The original
plan was to add `%global __pythondist_requires %{nil}` to every spec and let
the provides half keep the packages substitutable for distro ones. Building
in a real Leap 16.0 container showed that premise to be wrong, so the
decision was changed; the reasoning is kept because it is the reason the
change is safe.

What the container established:

- Leap 16's `/usr/lib/rpm/fileattrs/pythondist.attr` really does disable the
  requires half (`#disabled for now`) and leave the provides half active, so
  the diagnosis in "Context" stands.
- But that file drives generation by matching `%__pythondist_path`, a pattern
  for a flat *file* named `site-packages/<name>.dist-info`. A PEP 427 wheel
  unpacks to a *directory* `site-packages/<name>-<version>.dist-info/`
  containing `METADATA` and friends. No path in the built img2pdf RPM matches,
  so the generator never runs - for the provides or the requires.
- Leap 16's rpm 4.20.1 also has no `%generate_provides` spec section, so
  there is no way to invoke the generator by hand either.

Two A/B builds, rather than reading alone:

- Deleting `%global __pythondist_requires %{nil}` from
  `python313-img2pdf.spec` and rebuilding changes nothing: still zero
  `python3dist()` requires either way, so the macro suppressed nothing.
- The built `python313-img2pdf` RPM provides only
  `python313-img2pdf = 0.6.3.0-1.lp160.1`, with no `python3dist(img2pdf)`
  and no `python3.13dist(img2pdf)`.

A macro that looks load-bearing while doing nothing is worse than no macro:
it invites a future maintainer to trust a suppression that is not happening.
So the macro was removed from all ten specs, and the provides are simply
absent. Nothing in the verified install flow depends on them - tasks 3.4, 3.5
and both clean-room scenarios resolve every dependency by concrete
`python313-*` name, and Leap 16 is not consistent about these provides anyway:
its own `python313-Pillow` provides `python313-PIL`/`python3-PIL` but no
`python3dist(Pillow)`.

The residual cost is substitutability: a repo-oss or third-party package
that requires `python3dist(img2pdf) = 0.6.3` would not be satisfied by our
`python313-img2pdf`. No such requirement was observed - zero installed
packages on the build container require `python3dist(...)` at all - and the
cost of restoring it by hand is eight more maintained lines whose version
must track the unsuffixed upstream value, which is exactly the trap that
made the old `pdfminer.six` provides useless once `.0` was added. That trade
is recorded under "Open Questions".

Alternatives considered and rejected:

- `%global disable_python_dependency_generator 1`, the Fedora spelling.
  Rejected: that macro does not exist in Leap 16's `macros.python_all`, so
  it would be a silent no-op.
- Drop `BuildRequires: python-rpm-macros` so the attribute file is never
  installed. Rejected: the specs need `%{python3_sitelib}`,
  `%{python3_sitearch}` and `%autosetup` from it.
- Keep the macro as insurance for a future move to `%pyproject_install`,
  which does run the generators. Rejected as the same problem in milder
  form; a future maintainer who switches build style will find the
  generator firing from the spec's own `%pyproject_install` and can decide
  then.

### D3. Drop the hand-written `python3dist()` provides

`python3-pdfminer.six.spec` carried explicit
`Provides: python3dist(pdfminer.six)` and `python3dist(pdfminer-six)`
lines. They go, along with the comment that explains them.

The original justification was that the enabled generator already emits
`python3.13dist(pdfminer.six)` and `python3dist(pdfminer.six)`, making the
hand-written lines redundant. That is wrong, for the reason given in D2: the
generator does not fire, so it emits nothing and the hand-written lines were
the only source of those provides.

Removal still stands, on different grounds. The old lines used
`%{version}`, which is now the suffixed `20260107.0`, so keeping them
unchanged would have published a provide that a
`python3dist(pdfminer.six) = 20260107` requirement could not match anyway -
a wrong-valued provide is worse than none, because it looks like an answer.
The built `python313-pdfminer.six-20260107.0` RPM's provides are just
`python313-pdfminer.six = 20260107.0-1.lp160.1`, which is consistent with
D2: concrete name in, concrete name out.

### D4. Validate on a clean target, in two scenarios

Add one CI job that runs the collected runtime set through
`zypper -n install --allow-unsigned-rpm` in an `opensuse/leap:16.0`
container that has never seen a local build, across two scenarios:

- **stock** - default repositories only, nothing pre-installed. Catches
  unsatisfiable requires, wrong `Requires:` targets and missing runtime
  dependencies.
- **seeded** - repo-oss's `python313-sane` installed first, then our set.
  Catches the file-conflict class of bug, which the stock scenario cannot
  see because the colliding packages do not exist there.

Both scenarios assert on exit status with `-n` (which supplies
`--no-confirm`, so a file conflict aborts the transaction rather than
prompting) and additionally fail on `file conflicts` appearing in the
captured output, so the CI log says what went wrong instead of just
showing a non-zero status.

The seed comes from repo-oss only. Enabling `devel:languages:python` in CI
would be a non-deterministic third-party dependency with its own update
cadence. The EVR comparisons it produces are covered by D5's `.0` version
suffix, which is repository-independent.

### D5. A `.0` version suffix keeps our builds ahead, with no epoch

`python313-sane` has to satisfy three requirements at once: outrank Leap's
`2.9.2-bp160.1.1` so that `zypper update` cannot silently restore the
unpatched build, still yield to a future upstream 2.9.3, and do so without
an epoch. Only the first two are in tension, and the tension is in the
version field, not the release.

`Version: 2.9.2.0` with `Release: 1%{?dist}` resolves it, because a trailing
segment makes the version greater than `2.9.2` while leaving it below any
`2.9.3`. Verified with a port of `rpmvercmp`, comparing full EVRs the way
rpm does (epoch, then version, then release):

| Comparison | Result |
| --- | --- |
| `2.9.2.0-1.lp160.1` vs `2.9.2-bp160.1.1` | ours newer, on version |
| `2.9.3-bp160.1.1` vs `2.9.2.0-1.lp160.1` | theirs newer |
| `2.9.3rc1-1.lp160.1` vs `2.9.2.0-1.lp160.1` | theirs newer |
| `2.10-bp160.1.1` vs `2.9.2.0-1.lp160.1` | theirs newer |
| `2.9.2.0-2.lp160.1` vs `2.9.2.0-1.lp160.1` | ours newer, on release |

So our rebuilds install as upgrades over Leap's build, an upstream release
displaces ours normally, and no epoch is involved.

This is openSUSE's own documented idiom, listed among the sanctioned
solutions in the packaging versioning guidelines: "For the final release,
choose a version string that sorts after the upstream final but before any
future release... `Version: 1.8.0.beta2` for the prerelease, `Version:
1.8.0.0` for the final. This relies on the property that RPM sorts A-Z
before 0-9."

An epoch is rejected on two independent grounds. It is unnecessary once
the version is right, and the same guidelines "discourage and do not use
epochs", calling the field "considered harmful" and pointing at `zypper dup`
and `zypper in` instead. `~` does not help either: it sorts before
everything, which is the wrong direction.

The rule for the whole set is one sentence: **if a repository offers the
same package name at the same upstream version, append `.0` to our
`Version`.** That applies to `python313-sane` (`2.9.2.0`),
`python313-img2pdf` (`0.6.3.0`) and `python313-pdfminer.six`
(`20260107.0`), each verified against the build it competes with. For
`sane` the requirement is correctness - being replaced reverts the patch -
and for the other two it is that the installed set stays the one we tested,
which is the premise of the clean-room job. Packages already ahead on
version need nothing (`python313-tesserocr` 2.11.0 over 2.9.2,
`python313-python-iso639` 2026.7.23 over 2026.4.20), and neither do packages
no repository provides (`python313-ocrmypdf`, `-cysignals`,
`-setuptools-scm`, `-hatch-vcs`, `scantpaper`).

One practical consequence: `%{version}` is no longer the upstream version,
so the source URL must not use it. The upstream version moves into its own
macro, following the pattern the same guidelines give for exactly this:

```
%define pkg_version 2.9.2
Version:        2.9.2.0
Source:         .../python313-sane-%{pkg_version}.tar.gz
```

This affects the three affected specs, and `python313-sane` in particular
because its `%prep` and patch references must keep resolving against the
real tarball name.

No install command needs `--allow-downgrade`: our build is simply newer.
It remains useful only as a recovery step for a machine whose rpmdb was
already left inconsistent by the file-conflict bug this change fixes, where
`zypper in` on the artifact set is the documented way out.

### D6. Drop `--force-resolution` everywhere

`build.sh`'s `do_install`, both READMEs' install commands, and the
workflow drop `--force-resolution`, and the packaging README loses its
instruction to confirm the file-conflict prompt. That flag exists to make
zypper pick a resolution without asking; here it was suppressing exactly
the diagnosis we needed. For the same reason the conflict prompt must
never be answered `yes`: it leaves two packages owning one file.

### D7. The Fedora tree diverges on naming

`packaging/fedora/` keeps `python3-*` and its `python3dist()` references.
On Fedora `python3-*` is the package name and the `python3dist()` provides
exist, so the current Fedora specs are right. The two trees are no longer
expected to stay in step on naming, only on source versions and the
shared sane patch; `packaging/opensuse/README.md` records this so the
next person does not "fix" the divergence back.

## Risks / Trade-offs

- **Installing the set replaces third-party packages a user relies on.**
  Our `python313-tesserocr` 2.11.0 supersedes `devel:languages:python`'s
  2.9.2, and `python313-python-iso639` 2026.7.23 supersedes 2026.4.20,
  which may be what paperless-ng's own `ocrmypdf` resolves. → This is
  inherent to shipping dependencies under the distribution's own names,
  and it is strictly better than the status quo, where the files are
  clobbered without the rpmdb recording a replacement. Document the
  replacement and the removal path in `README.md`, and bump our versions
  above the third-party ones so zypper reads it as an upgrade where it
  can.

- **`Version:` no longer states the upstream version** for the three
  packages carrying a `.0` suffix, which is a real loss of clarity and can
  mislead a reader or a tool into thinking the upstream release is `2.9.2.0`.
  → Mitigated the way openSUSE's own guidelines prescribe, by keeping the
  true upstream version in `%define pkg_version` and using it for `Source:`
  (D5), and by documenting the rule in `packaging/opensuse/README.md` so
  the two numbers are never confused. A cosmetic consequence is that
  `rpm -q` and release filenames read `2.9.2.0` where upstream is `2.9.2`,
  which is the accepted cost of not using an epoch.

- **Suppressing the requires generator also suppresses genuinely useful
  ones.** Upstream `Requires-Dist` entries we do not map to a
  `python313-*` package are lost. → They are already lost: the specs
  declare their `Requires:` by hand (see the `pi-heif` note in
  `python3-ocrmypdf.spec`), and the generated set was unusable. The
  `%check` steps, which import each package, are the real check.

- **The clean-room job can pass while a user's machine still breaks,** if
  the user's set of third-party repos differs from repo-oss. → Accepted.
  The job removes the failures that are ours; it cannot enumerate every
  repository a user might have enabled.

- **Renaming changes published artifact filenames,** so existing
  instructions and any downloaded copies become stale. → Call it out in
  `README.md` and the release notes for the fix.

## Migration Plan

1. Land the spec renames, the generator suppression and the CI clean-room
   job together, so no commit exists in which the published RPMs are
   still named `python3-*` but the new test runs.
2. Rebuild all nine packages, publish a fresh artifact set under the new
   names, and note in the release that the `python3-*.rpm` files are
   superseded by the `python313-*.rpm` files.
3. Recovery for a user who already accepted a conflict prompt: remove the
   superseded third-party packages (`zypper remove python313-img2pdf
   python313-tesserocr python313-python-iso639` after installing the new
   set), then confirm with `rpm -V` that no file is left claimed by two
   packages. This is a documentation change, not an automated migration.

Rollback is a matter of reinstalling the previous artifact set; because
the new names differ from the old ones, a rollback leaves the old
`python3-*` packages and the new `python313-*` packages fighting over the
same files, so rollback means removing the `python313-*` set first.

## Open Questions

- ~~**Should `img2pdf` and `pdfminer.six` be packaged here at all?**~~
  **Resolved: keep both.** We package exactly the Python dependencies that the
  standard distribution does not ship. `python313-img2pdf` and
  `python313-pdfminer.six` are not in Leap 16 repo-oss - only in
  `devel:languages:python` - so they stay in the set, and so does every other
  dependency spec here. All ten specs (`python313-cysignals`,
  `python313-setuptools-scm`, `python313-hatch-vcs`, `python313-tesserocr`,
  `python313-python-iso639`, `python313-sane`, `python313-pdfminer.six`,
  `python313-img2pdf`, `python313-ocrmypdf` and `scantpaper`) are renamed and
  kept. This keeps the release self-contained: a user installs the RPMs and the
  third-party repository is never needed, the installed versions stay pinned to
  what CI tested, and the stock clean-room scenario (D4) can pass with no
  repository other than ours. The cost is two extra rebuilds in CI. The
  alternative - dropping both and requiring `devel:languages:python/16.0` - was
  rejected because it makes the installation instructions depend on a second
  repository whose update cadence we do not control, lets the dependency
  versions drift away from what we tested, and makes the stock scenario
  impossible. The maintainer confirmed the "package what the standard distro
  lacks" rule on 2026-10-03.

- Should `python313-ocrmypdf` be pinned to 16.11.1 for longer, or
  re-evaluated when Leap 16 gains a `python313-ocrmypdf` of its own? The
  answer depends on the distro's roadmap rather than on anything in this
  change, and does not affect the approach or the task breakdown, so it
  is left for the next packaging review.
- ~~**Should the rebuilt Python packages carry `python3dist()` provides, and
  should the `%global __pythondist_requires %{nil}` line stay?**~~ **Resolved
  2026-10-03: option 3, no provides and no macro.** D2 and D3 were both written
  on the assumption that the pythondist generator runs for these specs. Building
  in a real Leap 16.0 container shows it does not: its `%__pythondist_path`
  pattern predates PEP 427's directory-style `dist-info`, and Leap 16's rpm has
  no `%generate_provides` section to invoke it by hand. So the packages emit
  neither `python3dist()` requires nor provides, and the macro is inert.

  The maintainer chose to remove the macro and not hand-write the provides. The
  reasoning, kept because it is why the change is safe:

  - The macro was removed from all ten specs. A macro that looks load-bearing
    while doing nothing invites a future maintainer to trust a suppression that
    is not happening, so the cheaper-sounding option 1 ("keep it as insurance")
    was judged to be the same defect in milder form.
  - The provides are simply absent. Nothing in the verified install flow needs
    them: 3.4, 3.5 and both clean-room scenarios resolve every dependency by
    concrete `python313-*` name.
  - The substitutability loss is real but undemonstrated. No installed package
    on the build container requires `python3dist(...)` at all, and Leap 16 is
    not consistent about these provides - its own `python313-Pillow` provides
    `python313-PIL`/`python3-PIL` but no `python3dist(Pillow)`.
  - Hand-writing them would cost eight more maintained lines that must track
    each upstream rename and whose version must be the unsuffixed upstream
    value, which is exactly the trap that made the old `pdfminer.six` provides
    useless once `.0` was added.

  CI now asserts the decision instead of the macro spelling: no published RPM
  carries a `python3dist()` require, no spec hand-writes `python3dist()`
  metadata, and no spec reintroduces a suppression macro. If these packages ever
  move to `%pyproject_install`, that step is where the generator will start
  firing and the question needs revisiting.

  This changed an approved design decision and touched every spec, so the
  maintainer's direction was recorded before it was applied.
