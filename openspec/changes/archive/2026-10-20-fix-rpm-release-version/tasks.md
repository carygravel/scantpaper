## 1. Renderer tests first

- [x] 1.1 Add `src/scantpaper/tests/test_prepare_rpm.py` with a
      temporary git-repository fixture (commits, tags and a
      `pyproject.toml`) and invoke `dev/prepare_rpm.py` as a
      subprocess.
- [x] 1.2 Add a failing branch-build test: the rendered spec takes
      `Version:` from the ref's `pyproject.toml`, uses
      `Release: 0.<count>.g<sha>%{?dist}`, names the local source
      archive in `Source0`, and has a generated `%changelog` entry.
- [x] 1.3 Add failing tag tests: a `v<version>` tag whose
      `pyproject.toml` matches succeeds; a tag that disagrees fails
      and creates neither spec nor archive.
- [x] 1.4 Add a failing test that `--source-ref v3.0.24` on a repo
      whose HEAD is 4.0.0 renders 3.0.24 metadata and archives the
      v3.0.24 tree while using the current template.
- [x] 1.5 Add failing archive tests: the top-level directory is
      `scantpaper-<version>/`, tracked files are present, and
      modified or untracked worktree files are absent.
- [x] 1.6 Add failing changelog tests: the first entry matches the
      generated EVR and source-ref date, reuses the template's
      packager, distinguishes release from snapshot, preserves older
      entries, and uses English abbreviations under a non-C locale.
- [x] 1.7 Add failing error tests: a shallow repository, a missing
      placeholder, and a missing historical packager each fail with a
      clear message and leave no partial outputs.
- [x] 1.8 Run the new tests and record the expected failures before
      implementing.

## 2. Implement the renderer

- [x] 2.1 Add `dev/prepare_rpm.py` with a CLI taking
      `--template`, `--source-ref`, `--spec-out`, `--sources-dir` and
      `--repo-root`, plus pure helpers for version, release and
      changelog rendering.
- [x] 2.2 Read `pyproject.toml` from the source ref
      (`tomllib`/`tomli`), assert tag/version agreement, compute
      `git rev-list --count`, the short SHA and the commit date, and
      reject a shallow repository.
- [x] 2.3 Render `@VERSION@`, `@RELEASE@` and `@CHANGELOG@`; validate
      every placeholder before writing.
- [x] 2.4 Create `scantpaper-<version>.tar.gz` with `git archive` and
      write the spec and archive atomically, removing partial output
      on failure.
- [x] 2.5 Run the new tests until green.

## 3. Convert the specs and retire release-time bumping

- [x] 3.1 Replace `Version:` and `Release:` in both specs with
      placeholders, change `Source0` to
      `scantpaper-%{version}.tar.gz`, and add `@CHANGELOG@` after
      `%changelog`.
- [x] 3.2 Drop the interim `3.0.24-1` changelog entry from both
      templates (no 3.0.24 RPM was published) while keeping the
      historical `3.0.19-1` entry.
- [x] 3.3 Replace `src/scantpaper/tests/test_packaging_versions.py`
      with a template check asserting both specs contain the
      placeholders, contain no literal version, and contain no
      `Epoch:` line.
- [x] 3.4 Remove the spec paths, RPM date/changelog helpers and spec
      tests from `dev/release.py` and
      `src/scantpaper/tests/test_release.py`; restore the docstring,
      CLI help and fixtures to the three-file contract.
- [x] 3.5 Run the release tests and `dev/release.py --dry-run`; confirm
      it touches only `pyproject.toml`, `changelog.md` and the
      metainfo file.

## 4. Wire the build paths

- [x] 4.1 Both RPM workflows already accept `workflow_dispatch`.
- [x] 4.2 Add an optional `source_ref` dispatch input to both
      workflows, defaulting to `github.sha`, and pass it to the
      renderer.
- [x] 4.3 Set `fetch-depth: 0` on the checkout in both build jobs so
      commit counts and tags are available.
- [x] 4.4 In `packaging/opensuse/build.sh`, special-case `scantpaper`:
      render the spec and archive instead of copying the template and
      calling `fetch_source`; honour a `SOURCE_REF` environment
      variable for local builds.
- [x] 4.5 In the Fedora workflow, replace the `scantpaper` spec copy
      and `spectool` call with the renderer; leave the dependency
      builds unchanged.
- [x] 4.6 Re-check the retained installed-command tag assertions and
      the RPM install/collect globs against the new
      `0.<count>.g<sha>` filenames.
- [x] 4.7 Parse both workflow files and confirm the dependency cache
      keys and release-asset steps are otherwise unchanged.

## 5. Documentation

- [x] 5.1 Update `release_procedure.md`: `dev/release.py` handles
      three files again, RPM specs are build-time templates, and a
      release is identified by its tag rather than a `Release: 1`.
- [x] 5.2 Document `source_ref`, the `0.<count>.g<sha>` ordering rule,
      and the rule that only tagged builds are published in a dnf
      repository.
- [x] 5.3 Update `packaging/opensuse/README.md` and the Fedora
      packaging documentation: placeholders require the renderer,
      direct `rpmbuild` on a template fails, and local builds archive
      the selected commit.
- [x] 5.4 Update the `changelog.md` unreleased bullet to describe the
      build-time rendering, source-ref reproducibility and distro
      ordering, and check README installation wording for changed RPM
      names.

## 6. Quality gates

- [x] 6.1 Run `pytest`; all tests pass and coverage does not regress.
- [x] 6.2 Run `ruff format` and `ruff check` with no changes needed.
- [x] 6.3 Run `ty check .` with no diagnostics.
- [x] 6.4 Render both specs locally and inspect `Version:`,
      `Release:`, `Source0:`, the first changelog entry, and that no
      `@...@` placeholder or `Epoch:` remains.
- [x] 6.5 If rpm tooling is available, run `rpmspec -P` on both
      rendered specs; otherwise rely on the container builds in step
      7.1.

## 7. Recover the v3.0.24 RPM assets

- [ ] 7.1 After pushing, dispatch both workflows with
      `source_ref=v3.0.24`; confirm `scantpaper-3.0.24-0.<count>.g<sha>`
      names and an installed `scantpaper --version` of 3.0.24.
- [ ] 7.2 Delete the stale `scantpaper-3.0.19-*.rpm` assets from the
      v3.0.24 GitHub release and upload the rebuilt files (leave the
      wheel and `.deb` assets untouched).
- [ ] 7.3 Re-download the published RPMs, install them, and verify
      `scantpaper --version` reports 3.0.24.
