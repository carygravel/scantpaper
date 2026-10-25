# Tasks

## 1. Debian template tree

- [x] 1.1 Create `packaging/debian/` with `control`, `copyright`,
  `scantpaper.install`, `scantpaper.manpages`, `watch`, `upstream/metadata`
  and `source/format`, ported from the heredocs in
  `.github/workflows/deb.yml`; verify by diffing each file against the
  heredoc content, expecting only removed shell escaping (`\${misc:Depends}`)
  and removed unused expansions (`${HOMEPAGE:-...}`, `${GITHUB_REPO_NAME}`,
  `Architecture: all`)
- [x] 1.2 Add `packaging/debian/rules` with the unchanged makefile content and
  mode 100755; verify with `git ls-files -s packaging/debian/rules` showing
  `100755`
- [x] 1.3 Add `packaging/debian/changelog` with `@VERSION@`, `@DATE@` and
  `@TEXT@` placeholders and a static packager line; verify no literal version
  appears in the file and that `dpkg-parsechangelog` accepts it once the
  placeholders are substituted
- [x] 1.4 Extend `test_packaging_versions.py` to assert the changelog
  placeholders are present, no literal version is, and `rules` is executable
  in git; verify with
  `pytest src/scantpaper/tests/test_packaging_versions.py`

## 2. Renderer

- [x] 2.1 Implement version resolution in `dev/prepare_deb.py` - version from
  `pyproject.toml` at the ref, tag/version agreement, shallow-clone refusal,
  `<version>-0.<commit-count>.g<short-sha>`, and a commit-dated changelog
  using fixed English weekday and month names - with matching tests in
  `test_prepare_deb.py`; verify with
  `pytest src/scantpaper/tests/test_prepare_deb.py` and
  `git ls-files -s packaging/debian/rules`
- [x] 2.2 Implement tree materialisation: stream `git archive <ref>` into a
  temporary sibling of `build/deb/scantpaper-<version>/`, copy the templates
  into its `debian/`, render the changelog, ensure `rules` is executable, and
  swap the finished tree into place; add tests for the rendered file set, for
  exclusion of modified and untracked files, and for no output on failure
- [x] 2.3 Print the rendered version on success and verify it equals
  `dpkg-parsechangelog -S Version` in the rendered tree, so the workflow does
  not re-derive the version
- [x] 2.4 Write `packaging/debian/README.md` covering the template model, the
  scratch build tree, the local commands, and that salsa remains the
  authoritative Debian/Ubuntu packaging; verify the documented render and
  build commands run as written from a clean checkout

## 3. Workflow

- [x] 3.1 Replace the `Create control files` heredoc step and the unused
  `FIRST_YEAR`/`THIS_COMMIT_YEAR`/`THIS_COMMIT_DATE`/`YEAR_RANGE` block with
  a render step, and set `fetch-depth: 0`; verify the workflow contains no
  heredoc writing into `debian/` and no reference to the removed variables
- [x] 3.2 Point `mk-build-deps`, `debuild`, the artifact upload and the release
  upload at `build/deb/` and at the renderer's version output; verify the
  local commands from the README reproduce the same paths and globs
- [x] 3.3 Add `pull_request` and `workflow_dispatch` with an optional
  `source_ref`; verify a dispatch without the input renders the triggering
  commit and one with `source_ref=v4.0.1` renders that tag's version and tree
- [x] 3.4 Update `release_procedure.md` for the scratch build and the
  `.gitignore` constraint, and add a `changelog.md` entry describing the new
  `.deb` version format; verify the procedure names salsa as authoritative
  and the changelog entry matches the implemented format

## 4. Integration checks

- [x] 4.1 Run `pytest`, `ruff format --check`, `ruff check` and `ty check .`;
  verify all pass and that uncovered or partially covered lines did not
  increase
- [x] 4.2 Render and build locally, then verify `git status` at the repository
  root shows no `debian/` directory, `.gitignore` is unchanged, and
  `dpkg-deb --contents` lists the expected paths with no packaging templates
  installed
- [x] 4.3 Push the branch and verify the `pull_request` run builds and uploads
  a `.deb` whose version is `<version>-0.<commit-count>.g<short-sha>`

## Workflow follow-up

- Verify the next tagged release attaches the `.deb` asset and that the
  installed package reports the tag's version.
- Archive the change after the project's review requirements are satisfied.
