## Why

The published openSUSE Leap 16 RPMs do not install on a real Leap 16
machine. A user installing the documented single-transaction
`zypper install` command hits either an unsatisfiable dependency
(`python3dist(pluggy)`, `python3dist(pillow)`) or 14 file conflicts,
because the packages are named `python3-*` while Leap 16 and the
third-party OBS repos the user has enabled name the same modules
`python313-*`. Answering `yes` to the conflict prompt leaves the rpmdb
claiming two packages own the same files.

Three root causes, all verified against live repo metadata
(`distribution/leap/16.0/repo/oss` and `devel:languages:python/16.0`):

1. **Generated `python3dist()` requires.** *Originally diagnosed as a build
   defect; on inspection it is not one, and is recorded here because the
   original reading was plausible and wrong.* The claim was that rpm's
   `pythondist` dependency generator turns every upstream `Requires-Dist`
   into `Requires: python3dist(...)`, and that openSUSE disables that half
   for itself - Leap 16's `python-rpm-packaging` does ship
   `#%__pythondist_requires` commented out while keeping the provides half
   active. That much is true of the macro file. But the generator is driven
   by `%__pythondist_path`, which matches a flat `<name>.dist-info` *file*,
   and a PEP 427 wheel unpacks to a `<name>-<version>.dist-info/` *directory*,
   so it never fires for these pip-built specs. A rebuild with the
   suppression macro removed produces byte-identical dependency metadata.
   The packages emitted no `python3dist()` requires to begin with, and the
   remediation is accordingly to declare dependencies by concrete name and
   leave the generator alone (D2). What made the names unsatisfiable in
   practice is unchanged: `devel:languages:python` provides no
   `python3dist(...)` on any of `pluggy`, `rich`, `Pillow`, `sane`,
   `tesserocr`, `python-iso639` or `pdfminer.six`, and the newest repo-oss
   `python313-Pillow` build has dropped the provide too.

2. **Wrong package-name namespace.** On Leap 16 `python313-foo` is the
   package; `python3-foo` is only a provide. Naming our RPMs `python3-*`
   makes each one a *second* package for a module the user's system already
   has, so rpm reports file conflicts instead of performing an upgrade.

3. **A wrong bring-up premise.** The original proposal recorded that a
   probe of Leap 16.0 showed `python3-sane` absent. It is present as
   `python313-sane` 2.9.2, and the probe missed it for the same
   name-namespace reason. `img2pdf` and `iso639` are likewise already
   packaged on the user's system via third-party repos.

A fourth, structural gap let all of this ship: every `Verify` step in
`opensuse.yml` runs inside the build container, where each dependency is
satisfied by another RPM we just built. That check cannot see an
unsatisfiable require against repo-oss, or a file conflict with a distro
package, because the build machine is self-fulfilling by construction.

## What Changes

- Rename every openSUSE Python dependency package `python3-*` to
  `python313-*`, so our packages replace the distro's (or the third-party
  repos') package for the same module rather than colliding with it.
  **BREAKING**: the published artifact filenames change, so the install
  command and the release-asset names change with them.
- Explicitly disable rpm's `python3dist()` dependency generator in the
  specs, and add a CI assertion that no built RPM carries a
  `python3dist()` require.
- Drop the hand-written `Provides: python3dist(pdfminer.six)` /
  `python3dist(pdfminer-six)` lines; keep providing the concrete
  `python313-*` and `python3-*` names only.
- Fix `python313-sane`'s `%description`, which currently credits the
  vendored PR-109 patch with making a `python3dist()` provide match. The
  patch fixes a real `snap()` bug and needs no such justification. The
  rebuild stays: the patch is required, and Leap's `python313-sane` 2.9.2
  carries the unpatched bug.
- Correct the `scantpaper` RPM's own `Requires:` to the renamed packages.
- Give the three packages that a repository also offers at the same
  upstream version a `.0` version suffix (`2.9.2.0`, `0.6.3.0`,
  `20260107.0`), following openSUSE's documented idiom for "sorts after the
  upstream final but before any future release". This keeps our patched
  `sane` build from being silently replaced by Leap's unpatched build on
  the user's next `zypper update`, while still yielding normally to a
  future upstream 2.9.3 - and it needs no epoch, which openSUSE's guidelines
  discourage.
- Add a CI job that installs the collected runtime set into a **stock**
  `opensuse/leap:16.0` container with no extra repositories and no
  interactive prompts, plus a second variant seeded with the packages our
  artifacts overlap, asserting a conflict-free install in both **and**
  asserting that a subsequent `zypper update` leaves our packages in
  place.
- Correct the packaging documentation: remove `--force-resolution` and the
  advice to confirm the file-conflict prompt, replace the inverted
  `python3dist()` guidance in `packaging/opensuse/README.md`, and note
  that installing the set replaces the third-party packages of the same
  name.

## Capabilities

### New Capabilities

- None. This change alters packaging metadata and CI validation only; no
  application behaviour changes, so no capability specs are produced (see
  `skip_specs: true` in `.openspec.yaml`).

### Modified Capabilities

- None.

## Impact

- **Renamed files**: `packaging/opensuse/python3-{cysignals,tesserocr,
  iso639,sane,img2pdf,pdfminer.six,ocrmypdf,setuptools-scm,hatch-vcs}
  .spec` become `python313-*.spec`; their `Name:`/`%{name}` and the
  inter-spec `BuildRequires:`/`Requires:`/`Provides:` references move
  together. The shared file list
  `%{_builddir}/%{name}-files.list` follows automatically.
- **Modified files**: `packaging/opensuse/scantpaper.spec` (its
  `BuildRequires:`/`Requires:` block), `packaging/opensuse/build.sh` (the
  per-package cache copy globs and the artifact name),
  `.github/workflows/opensuse.yml` (cache globs, verify steps, the new
  clean-room install job), `packaging/opensuse/README.md`,
  `README.md` (openSUSE install section).
- **Fedora tree**: unchanged. `packaging/fedora/` builds for Fedora 43/44,
  where `python3-*` is the correct name and `python3dist()` provides still
  exist, so the two trees must now be allowed to diverge in package
  naming. The shared `python3-sane-snap-params-cache.patch` stays common.
- **Users**: existing installs from earlier releases are unaffected in
  content but must be upgraded by name, and the fix releases a new
  artifact set. A user who already accepted a conflict prompt holds an
  inconsistent rpmdb that needs `rpm -V` checking and removal of the
  superseded third-party packages.
- **Risk**: renaming means installing our set *replaces* the user's
  third-party `python313-tesserocr`, `-img2pdf` and `-python-iso639`. That
  is intentional and reversible, and strictly better than today's silent
  file-level clobber, but it can affect other consumers on the same
  machine (for example `ocrmypdf` under paperless-ng). This must be
  documented rather than silently imposed.