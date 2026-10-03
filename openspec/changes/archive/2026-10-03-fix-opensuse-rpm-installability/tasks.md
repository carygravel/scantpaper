# Tasks: fix openSUSE RPM installability

## 1. Rename the dependency packages to the Leap 16 namespace

- [x] 1.1 `git mv` the nine dependency specs to their Leap 16 names:
      `python3-cysignals.spec` -> `python313-cysignals.spec`,
      `python3-setuptools-scm.spec` -> `python313-setuptools-scm.spec`,
      `python3-hatch-vcs.spec` -> `python313-hatch-vcs.spec`,
      `python3-tesserocr.spec` -> `python313-tesserocr.spec`,
      `python3-iso639.spec` -> `python313-python-iso639.spec` (named after
      the PyPI distribution `python-iso639`, not the import name, so it
      matches the `python313-python-iso639` a third-party repo already
      publishes), `python3-sane.spec` -> `python313-sane.spec`,
      `python3-pdfminer.six.spec` -> `python313-pdfminer.six.spec`,
      `python3-img2pdf.spec` -> `python313-img2pdf.spec`,
      `python3-ocrmypdf.spec` -> `python313-ocrmypdf.spec`. Verify all
      nine are tracked by git and `ls packaging/opensuse/*.spec` shows no
      remaining `python3-*.spec`.
- [x] 1.2 Change each spec's `Name:` to match its new filename. The
      specs already derive the file list and doc paths from `%{name}`, so
      no other field should need editing. Verify with `rpmspec -P
      packaging/opensuse/python313-*.spec | grep -E '^(Name|%doc)'` on a
      Leap 16.0 container: every `Name:` matches its filename.
- [x] 1.3 Update the cross-references between the dependency specs:
      `python313-tesserocr` requires `python313-cysignals >= 1.11.4`,
      `python313-ocrmypdf` requires `python313-img2pdf` and
      `python313-pdfminer.six`, and the ocrmypdf spec's BuildRequires on
      `python313-hatch-vcs`/`python313-setuptools-scm`. Verify no spec
      still names a `python3-*` sibling: `grep -n 'python3-[a-z]' ...`
      returns only the deliberate `python3-sitelib`-style macro uses and
      the `python3-rpm-macros`/`python3-base` BuildRequires.
- [x] 1.4 Update `packaging/opensuse/scantpaper.spec`: the `BuildRequires:`
      block at the top and the runtime `Requires:` block that currently
      reads `python3-{img2pdf,ocrmypdf,iso639,sane,tesserocr}` become the
      `python313-*` names, including
      `Requires: python313-python-iso639`. Rewrite the comment above the
      `Requires:` block, which currently argues for concrete names on the
      grounds that third-party repos lack `python3dist(...)`, so it states
      the real reason instead. Verify `rpmspec -P` expands and that
      `rpm -qp --requires` on the built RPM lists only names this change
      can actually produce.
- [x] 1.5 Update `packaging/opensuse/build.sh`: the `spec_for` and
      `rpmname_for` case arms, and the comments above `ORDER`/`RUNTIME`
      that name the two build-only helpers. Leave `patch_for` alone (it
      returns the patch filename, not a package name). Verify
      `bash -n packaging/opensuse/build.sh` and that
      `for k in cysignals setuptools-scm hatch-vcs tesserocr iso639 sane
      pdfminer img2pdf ocrmypdf scantpaper; do` prints a spec file that
      exists for every key.
- [x] 1.6 Update `.github/workflows/opensuse.yml`: every
      `cp ~/rpmbuild/RPMS/*/python3-<pkg>-*.rpm` cache copy glob, and the
      `rpm -q` argument lists in the three "Verify" steps. Verify by
      grepping the workflow for `python3-`: no build, cache or verify step
      may still reference a renamed package, and `python3-rpm-macros`
      (a BuildRequires, not a package we ship) is the only expected hit.
- [x] 1.7 Bump the spec cache keys so the renames cannot be served from a
      pre-rename cache entry: add a `-v2` suffix (or equivalent) to the
      openSUSE cache keys in `opensuse.yml`, or confirm that the existing
      `hashFiles(...)` keys already change because the spec filenames they
      hash have moved. Verify by reading the resulting key strings and
      confirming none of them can match a cache populated before this
      change.

- [x] 1.8 Resolve the open question in `design.md` before building
      anything: decide whether `python313-img2pdf` and
      `python313-pdfminer.six` stay in the set or are dropped in favour of
      requiring `devel:languages:python`. **Resolved 2026-10-03: keep
      both.** Neither is in Leap 16 repo-oss - only in
      `devel:languages:python` - so the rule is to package what the standard
      distribution does not ship. All ten specs are renamed and kept; the
      release stays self-contained and the stock clean-room scenario in 4.2
      remains viable. The decision is recorded under "Open Questions" in
      `design.md`. Sections 1 and 4 needed no scope change, and the rename
      and `.0` version work is unaffected.

## 2. Remove the generated python3dist requires and the hand-written provides

- [x] 2.1 Add `%global __pythondist_requires %{nil}` to each of the nine
      renamed specs, immediately after `Name:`/`Version:`/`Release:` and
      before any BuildRequires, with a comment recording *why* - that
      Leap 16's own `python-rpm-packaging` ships the requires half of the
      generator disabled, that we must match it, and that the provides
      half stays on deliberately. Verify `rpmspec -P` on a Leap 16.0
      container still expands each spec, and that the macro is defined in
      the expanded output rather than leaking through unexpanded.

      **Verified 2026-10-03.** `rpmspec -P` is clean on all ten specs in a
      real Leap 16.0 container, with no "macro expanded in comment"
      warnings. Leap 16's `/usr/lib/rpm/fileattrs/pythondist.attr` does
      confirm the premise:

      ```
      %__pythondist_provides   .../pythondistdeps.py --provides --majorver-provides
      #disabled for now
      #%__pythondist_requires  .../pythondistdeps.py --requires
      ```

      **Superseded 2026-10-03; the macro was removed.** 2.2 proved the line is
      a no-op for these specs, and the maintainer chose to drop it rather than
      keep it as insurance (see the resolved entry in "Open Questions" in
      `design.md`). The macro and its comment are gone from all ten specs. Net
      result of this task: no spec suppresses the pythondist generator, and CI
      now asserts that so a macro cannot creep back in.
- [ ] 2.2 Build one representative package (the cheapest: `python313-
      img2pdf`) and confirm the generated requires are gone:
      `rpm -qp --requires ~/rpmbuild/RPMS/noarch/python313-img2pdf-*.rpm`
      contains no `python3dist(`, while `rpm -qp --provides` still
      contains `python3dist(img2pdf)` and `python3.13dist(img2pdf)`.

      **Measured 2026-10-03; the provides half is false as written, and is no
      longer a goal.** This box stays unticked on purpose - the task asserts
      something the build disproves, and ticking it would record a falsehood.
      The decision that replaced it is recorded in "Open Questions" in
      `design.md` (option 3: no provides, no macro). In a real Leap 16.0
      container the built `python313-img2pdf-0.6.3.0` RPM gives:

      ```
      Requires: python313-Pillow, python313-pikepdf   (no python3dist( at all)
      Provides: python313-img2pdf = 0.6.3.0-1.lp160.1   (and nothing else)
      ```

      So the requires are absent as required, but so are the
      `python3dist(img2pdf)` / `python3.13dist(img2pdf)` provides, because
      the generator never runs. Two A/B builds establish the cause:

      - Deleting `%global __pythondist_requires %{nil}` and rebuilding
        changes nothing - still zero `python3dist()` requires. The macro is
        not what removes them; nothing ever adds them.
      - The generator is driven by `%__pythondist_path` in
        `pythondist.attr`, which matches a flat *file*
        `site-packages/<name>.dist-info`. A PEP 427 wheel unpacks to a
        *directory* `site-packages/<name>-<version>.dist-info/`, and no
        path in the built RPM matches:

        ```
        no match /usr/lib/python3.13/site-packages/img2pdf-0.6.3.dist-info/METADATA
        ```

        Leap 16's rpm 4.20.1 also has no `%generate_provides` spec
        section, so the generator cannot be invoked by hand either.

      Nothing in the verified install flow (tasks 3.4, 3.5 and the 4.2
      scenarios) depends on these provides: every dependency is resolved by
      concrete `python313-*` names. Zero installed packages on the build
      container require `python3dist(...)` at all.
- [x] 2.3 Drop the explicit `Provides: python3dist(pdfminer.six)` and
      `Provides: python3dist(pdfminer-six)` lines from
      `python313-pdfminer.six.spec`, together with the comment block that
      explains them; the enabled generator emits the `pdfminer.six`
      spelling from the installed metadata, so the hand-written lines are
      redundant and the `pdfminer-six` one is a PEP 503 normalisation the
      generator does not produce by default. Verify the built RPM's
      provides contain `python3dist(pdfminer.six)` and no
      `python3dist(pdfminer-six)`.

      **Verified 2026-10-03, with the stated justification withdrawn.**
      The lines are gone and the built
      `python313-pdfminer.six-20260107.0` RPM contains no
      `python3dist(pdfminer-six)`. But it also contains no
      `python3dist(pdfminer.six)`, because the generator does not fire (see
      2.2), so "the generator emits it for us" is not true. The removal
      still stands: the old lines used `%{version}`, now the suffixed
      `20260107.0`, so a retained provide could not satisfy a
      `python3dist(pdfminer.six) = 20260107` requirement either. The
      built RPM's provides are just `python313-pdfminer.six =
      20260107.0-1.lp160.1`.
- [x] 2.4 Confirm no spec reintroduces a `python3dist()` require by hand:
      `grep -rn 'Requires:.*python3dist' packaging/opensuse/` must return
      nothing. This is the check that would have caught the original
      defect at review time rather than on a user's machine.

## 3. Keep our builds ahead of same-version repository builds

- [x] 3.1 Append `.0` to the `Version:` of the three specs a repository
      also provides at the same upstream version: `python313-sane.spec`
      (`2.9.2.0`), `python313-img2pdf.spec` (`0.6.3.0`) and
      `python313-pdfminer.six.spec` (`20260107.0`). Leave the other five
      dependency specs and `scantpaper.spec` at the plain upstream version.
      Comment the rule next to each one: a repository offers this package
      at the same upstream version, so a trailing segment keeps us ahead
      without an epoch (D5). Verify no spec gains an `Epoch:` -
      `grep -rn '^Epoch:' packaging/opensuse/` must return nothing.
- [x] 3.2 In each of the three specs, move the real upstream version into
      `%define pkg_version <upstream>` and use `%{pkg_version}` in `Source:`
      and anywhere else the tarball name appears, keeping `Version:` as the
      suffixed value. This is the pattern openSUSE's versioning guidelines
      give for a `Version:` that no longer matches upstream. Verify
      `rpmspec -P` expands the real tarball name, that the source still
      fetches, and that `python313-sane`'s `%prep` and `%patch` references
      still apply - that spec has the most filename-sensitive lines.
- [x] 3.3 Assert the ordering deterministically rather than by eye, using
      `rpmdev-vercmp` (or `rpm --compare-versions`):
      `2.9.2.0` > `2.9.2`; `2.9.3` > `2.9.2.0`; `2.9.3rc1` > `2.9.2.0`;
      `2.10` > `2.9.2.0`; `0.6.3.0` > `0.6.3`; `20260107.0` > `20260107`;
      and `2.9.2.0-2.lp160.1` > `2.9.2.0-1.lp160.1` so our own rebuilds
      install as upgrades. Record the command and its output in the change,
      since this is the property the whole approach rests on.

      **Verified 2026-10-03.** `rpmdev-vercmp`, `rpm` and `podman`/`docker`
      are all absent from the development machine, so the assertions were run
      with a port of rpm's own `rpmvercmp()` algorithm (from
      `lib/rpmvercmp.c`), self-tested first against cases whose answers rpm's
      documented rules fix unambiguously (`2.10` > `2.9` numeric-not-lexical,
      `1.0~rc1` < `1.0` tilde-sorts-first, `1.0` < `1.0.0`, `1.0` < `1.0.1`).

      Version-only comparisons:

      | Comparison | Result |
      | --- | --- |
      | `2.9.2.0` vs `2.9.2` | +1 (ours newer) |
      | `2.9.3` vs `2.9.2.0` | +1 (theirs newer) |
      | `2.9.3rc1` vs `2.9.2.0` | +1 (theirs newer) |
      | `2.10` vs `2.9.2.0` | +1 (theirs newer) |
      | `0.6.3.0` vs `0.6.3` | +1 (ours newer) |
      | `20260107.0` vs `20260107` | +1 (ours newer) |

      Full EVRs, comparing epoch, then version, then release the way rpm
      does. Every epoch is 0, so it is left out of the strings:

      | Ours | Theirs | Result |
      | --- | --- | --- |
      | `2.9.2.0-1.lp160.1` | `2.9.2-bp160.1.1` | +1 (ours, on version) |
      | `2.9.2.0-2.lp160.1` | `2.9.2.0-1.lp160.1` | +1 (ours, on release) |
      | `2.9.2.0-1.lp160.1` | `2.9.3-bp160.1.1` | -1 (upstream) |
      | `0.6.3.0-1.lp160.1` | `0.6.3-lp160.23.2` | +1 (ours) |
      | `20260107.0-1.lp160.1` | `20260107-lp160.29.3` | +1 (ours) |
      | `20260107.0-1.lp160.1` | `20260107.1-lp160.1` | -1 (upstream) |

      Every required assertion holds, including the two that constrain the
      design: the suffix must outrank a same-upstream-version build with an
      alphabetic release (`bp160`), and it must not shadow a genuine future
      upstream bump.

      **Re-verified 2026-10-03 inside a real Leap 16.0 container with rpm's
      own comparison code** (`python3-rpm`'s `rpm.labelCompare`, which is the
      same `rpmvercmp` algorithm rpm uses to resolve dependencies). Neither
      `rpmdev-vercmp` nor `rpm --compare-versions` exists in Leap 16.0's rpm
      4.20.1, so `rpm.labelCompare` is the closest available equivalent and is
      stronger than the port, being rpm's own code rather than a copy of it.
      Every row above reproduces exactly:

      | Comparison | `rpm.labelCompare` |
      | --- | --- |
      | `2.9.2.0` vs `2.9.2` | newer (ours) |
      | `2.9.3` vs `2.9.2.0` | newer (theirs) |
      | `2.9.3rc1` vs `2.9.2.0` | newer (theirs) |
      | `2.10` vs `2.9.2.0` | newer (theirs) |
      | `0.6.3.0` vs `0.6.3` | newer (ours) |
      | `20260107.0` vs `20260107` | newer (ours) |
      | `2.9.2.0-1.lp160.1` vs `2.9.2-bp160.1.1` | newer (ours, on version) |
      | `2.9.2.0-2.lp160.1` vs `2.9.2.0-1.lp160.1` | newer (ours, on release) |
      | `2.9.2.0-1.lp160.1` vs `2.9.3-bp160.1.1` | older (upstream wins) |
      | `20260107.0-1.lp160.1` vs `20260107.1-lp160.1` | older (upstream wins) |
- [x] 3.4 Verified in a real Leap 16.0 container: install Leap's
      `python313-sane` 2.9.2 first, then install our artifact over it with
      **no** extra zypper flags, and confirm the transaction succeeds as an
      upgrade rather than being refused.

      **Verified 2026-10-03.** Observed on `opensuse/leap:16.0`:

      ```
      seeded:     python313-sane-2.9.2-160000.x.x86_64
      ZYPPER_RC=0
      after install: python313-sane-2.9.2.0-1.lp160.1.x86_64
      ```

      Our epoch-free `2.9.2.0` supersedes the distro's `2.9.2` as a normal
      upgrade. No `--force-resolution`, no `--allow-downgrade`, no epoch.
- [x] 3.5 Prove the durability property the suffix exists for: after 3.4,
      run `zypper -n update` (or `dist-upgrade`) and confirm
      `rpm -q python313-sane` still reports our build
      (`2.9.2.0-1.lp160.1...`), not Leap's. Record the observed output so
      the regression this guards against cannot silently return. This check
      belongs in CI - see 4.6.

      **Verified 2026-10-03**, continuing the same container as 3.4:

      ```
      after install: python313-sane-2.9.2.0-1.lp160.1.x86_64
      $ zypper -n --gpg-auto-import-keys update
      after update:  python313-sane-2.9.2.0-1.lp160.1.x86_64
      ```

      Our build survives a full `zypper update`. The negative case is also
      confirmed: rebuilding with `Version: 2.9.2` (no suffix) leaves the
      distro's package winning, which is the regression 3.5 exists to catch.

- [x] 3.6 Fix `python313-sane.spec`'s `%description`, which credits the
      vendored PR-109 patch with making a `python3dist(python-sane)` provide
      match what scantpaper expects. The patch fixes a real `snap()` bug and
      needs no such justification; state the `SaneDev.snap()` /
      `SANE_STATUS_INVAL` behaviour it actually corrects.

## 4. Prove the packages install on a clean target

- [x] 4.1 Remove `--force-resolution` from `do_install` in
      `packaging/opensuse/build.sh` and from every local `zypper install`
      in `.github/workflows/opensuse.yml`. Verify by grep: no
      `--force-resolution` remains in either file.
- [x] 4.2 Add a clean-room install job to `.github/workflows/opensuse.yml`
      that runs after "Copy packages", in an `opensuse/leap:16.0`
      container with no extra repositories, over a two-entry matrix:
      `stock` (default repos, nothing pre-installed) and `seeded` (see
      4.3). Each entry runs
      `zypper -n install --allow-unsigned-rpm artifacts/*.rpm`, asserts a
      zero exit status, and additionally fails if `file conflicts` appears
      in the captured output so the log names the offending files. The job
      consumes the uploaded artifact rather than rebuilding, so it tests
      exactly what is published.

      **Verified 2026-10-03 against a real Leap 16.0 container, and two
      defects in the first draft were found and fixed.** Both would have
      made this job fail on a correct build:

      - *The conflict check never ran on failure.* GitHub executes `run`
        blocks with `bash -e`, so a bare `zypper ... > log; rc=$?` aborts
        the step on the failing `zypper` and never reaches the log dump or
        the conflict check. The status is now captured in an
        `if zypper ...; then rc=0; else rc=$?; fi`.
      - *The conflict check fired on success.* zypper prints
        `Checking for file conflicts: [.......done]` on **every** run,
        success included, so `grep -i 'file conflicts'` matched a healthy
        install. The assertion now matches only a real conflict -
        `Detected N file conflict` / `conflicts with file from package` -
        which is what zypper actually prints:

        ```
        Checking for file conflicts: [..error]
        Detected 1 file conflict:
        ```

      Both directions are now checked against real zypper output: the full
      artifact set over stock Leap reports no conflict and the step passes,
      and a probe RPM deliberately colliding with a file `python313-sane`
      owns produces the `Detected 1 file conflict` text and fails the step.
- [x] 4.3 In the `seeded` entry, install `python313-sane` from repo-oss
      first, before installing our artifact set, so the transaction
      overlaps a package the target already owns. Seed from repo-oss only
      - not from `devel:languages:python` - so the job has no
      non-deterministic third-party dependency. Verify the seed is
      present (`rpm -q python313-sane`) before the artifact install runs.

      **Verified 2026-10-03** - see the 3.4 and 3.5 transcripts, which are
      this scenario run by hand.
- [x] 4.4 Add a metadata assertion over the built RPMs that fails if any
        of them carries a `python3dist(` require. Verify by temporarily
        adding a `python3dist()` require to a scratch spec and confirming
        the assertion fails, then reverting.

        **Revised 2026-10-03.** This task originally also pinned the macro
        spelling so the Fedora-style `disable_python_dependency_generator`
        could not be substituted as a silent no-op. There is no macro left to
        pin (see 2.1), so that half is replaced by the invariant that
        actually matters: a second assertion fails the build if any spec
        hand-writes `python3dist()` requires or provides, or reintroduces a
        generator-suppression macro of either spelling. That way the
        decision cannot be quietly undone in either direction.
- [x] 4.5 Confirm the pre-existing "Verify" steps still make sense after
      the rename, and add the end-to-end runtime check the build container
      could never give us: after the clean-room install, run the installed
      `scantpaper --version` (or an equivalent import of `sane`,
      `tesserocr`, `iso639`, `img2pdf`, `ocrmypdf`) from the seeded
      container. Verify it succeeds against the artifact set rather than
      against the build tree.
- [x] 4.6 Make the `seeded` entry assert the durability property, not just
      the install: after installing our artifact set over Leap's seeded
      `python313-sane`, run `zypper -n update` and require that
      `rpm -q python313-sane` still reports our `2.9.2.0` build. An install
      that succeeds and is then reverted by the next update is the failure
      mode D5 exists to prevent, so a green run that only checks the exit
      status of the install would miss it. Verify by temporarily reverting
      `Version:` in `python313-sane.spec` to plain `2.9.2`, rebuilding, and
      confirming this assertion fails with Leap's version - then revert.

## 5. Documentation

- [x] 5.1 Rewrite the "Concrete `python313-*` requires, not `python3dist`
      ..." bullet in `packaging/opensuse/README.md`. Its reasoning is
      inverted: it is true that third-party repos lack the `python3dist`
      provides, and the conclusion drawn from that was to require concrete
      names - but the actual defect was requiring `python3dist()` *at
      all*. Replace it with the naming rule (one name per module, taken
      from the PyPI project name) and the rule that no spec may depend on
      a `python3dist()` provide.
- [x] 5.2 In the same file, remove the `--force-resolution` flag and the
      instruction to confirm the file-conflict prompt from the install
      example, and add a bullet recording that the Fedora and openSUSE
      trees now differ in package naming by design (D7) so the divergence
      is not "fixed" back. Verify the example carries neither flag:
      `--force-resolution` and `--allow-downgrade` must both be absent, the
      latter because D5 makes it unnecessary.
- [x] 5.3 Add a bullet to `packaging/opensuse/README.md` explaining that
      installing the set *replaces* same-named packages from repo-oss and
      third-party repos, that this is intended, and how to check for and
      recover from a previously clobbered rpmdb (`rpm -V`, removing the
      superseded third-party packages).
- [x] 5.4 Add a second bullet to the same file on the `.0` version suffix:
      `python313-sane`, `python313-img2pdf` and `python313-pdfminer.six`
      carry a trailing `.0` so they stay ahead of the same-named
      distribution builds and a system update cannot swap Leap's unpatched
      `sane` for ours. State the rule ("a repository offers this package at
      the same upstream version, so add a trailing segment"), note that it
      follows openSUSE's documented idiom and deliberately avoids an epoch,
      and warn the reader that `%{version}` is therefore *not* the upstream
      version - `2.9.2.0` is our 2.9.2. Give the removal path back to
      Leap's package for a user who prefers it, and say that `zypper in` on
      the artifact set is how to recover a machine whose rpmdb was left
      inconsistent by the file-conflict bug.
- [x] 5.5 Update the openSUSE install section in the top-level
      `README.md`: the new `python313-*.rpm` filenames and a short note
      that the set replaces same-named third-party packages. Verify no
      stale `python3-*.rpm` filename remains, that neither install flag
      appears, and that all lines stay within 80 columns.

## 6. Quality gates

- [x] 6.1 Confirm the change touches no application source or test:
      `pytest` (coverage at or above the current 99%), `ruff format
      --check .`, `ruff check .` and `ty check .` all stay clean and
      unchanged.
- [x] 6.2 Run `openspec validate fix-opensuse-rpm-installability` (or
      the schema's equivalent) and confirm the change is accepted with its
      `skip_specs: true` marker.
- [x] 6.3 Push a branch and confirm the full workflow is green end to end:
      all nine packages build under the new names, the clean-room job
      passes both matrix entries, and a tag run attaches the
      `scantpaper-opensuse-leap16` artifact under the new filenames.

      **Verified 2026-10-03.** The maintainer pushed the branch and
      reported the workflow green end to end, which closes the task for
      the two matrix entries and the artifact filenames. That run is also
      the first exercise of the clean-room job as committed, so the two
      defects recorded under 4.2 - the `bash -e` abort and the
      false-positive conflict grep - are confirmed fixed in CI and not only
      against a local container.
- [x] 6.4 Record in `changelog.md` that the published openSUSE artifact
      names changed, so users of the previous release set are not left
      installing superseded `python3-*.rpm` files.

## Remaining tasks

One task is deliberately unticked, and it is not waiting on anything.

- **2.2** - the assertion is false as written, so it cannot be ticked as
  phrased: ticking it would record something the build disproved. Its two
  halves were both checked in a real Leap 16.0 container. The built
  `python313-img2pdf-0.6.3.0` RPM contains no `python3dist()` require, as
  required, but it also contains no `python3dist(img2pdf)` or
  `python3.13dist(img2pdf)` provide, because the pythondist generator never
  fires for these pip-built wheels. That is no longer outstanding: the
  maintainer decided on 2026-10-03 to accept the absence and drop the inert
  suppression macro too (option 3 under "Open Questions" in `design.md`), and
  the resulting packaging change is applied and recorded under 2.1 and 4.4.

The tooling gaps that used to hold tasks back are gone. `podman` is now
available, so 3.4 and 3.5 were verified against a real Leap 16.0 container
rather than a stub, and 3.3's ordering assertions were re-run with rpm's
own `rpm.labelCompare` instead of a port of `rpmvercmp()`. Neither
`rpmdev-vercmp` nor `rpm --compare-versions` exists in Leap 16.0's rpm
4.20.1, so `rpm.labelCompare` is the closest available equivalent - and a
stronger one, being rpm's own code rather than a copy of it.
