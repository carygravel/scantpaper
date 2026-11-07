# Tasks

## 1. Bundle builder

- [x] 1.1 Add `dev/make_release_bundle.py` with `--target`, `--input`,
  `--output` and an optional `--version`. It accepts exactly `fedora-43`,
  `fedora-44`, `opensuse-leap-16.0` and `opensuse-tumbleweed` and rejects
  anything else before writing. Verify
  `python3 dev/make_release_bundle.py --target bogus --input X --output Y`
  exits non-zero and leaves no output.
- [x] 1.2 Derive the version from the built `scantpaper-<version>-...rpm`
  when `--version` is absent, exclude `*-debuginfo-*` and
  `*-debugsource-*`, require the application RPM, and fail when no RPM
  remains. Verify with a fixture containing an application RPM and a debug
  RPM that the debug package is absent and the application package is
  present.
- [x] 1.3 Stage `scantpaper-<version>-<target>/`, write `SHA256SUMS`
  covering every staged RPM and `INSTALL.txt` with the target's
  one-transaction command (`dnf` or `zypper --allow-unsigned-rpm`), and
  create the `.tar.gz`. Verify extraction, `sha256sum -c SHA256SUMS`, and
  the install command for each target.
- [x] 1.4 Sort tar members and normalize ownership and mtime. Verify two
  builds from the same staging directory have the same member list and
  normalized metadata, and that the archive name and top-level directory
  match the target and version.
- [x] 1.5 Add `dev/tests/test_make_release_bundle.py` covering unsupported
  target, version discovery and override, debug exclusion, missing
  application RPM, layout, checksums, install note, naming and member
  order. Verify `python3 -m pytest dev/tests/test_make_release_bundle.py`
  passes, and `ruff check` and `ruff format --check` are clean for the new
  files.

## 2. Fedora and openSUSE workflows

- [x] 2.1 In `.github/workflows/fedora.yml`, keep the existing
  `artifacts/*.rpm` CI artifact upload, run the builder for
  `fedora-${{ matrix.fedora }}` into `dist/`, and release only
  `dist/*.tar.gz`. Verify the workflow YAML parses, the builder step names
  the matrix target, and the release step no longer matches RPMs.
- [x] 2.2 In `.github/workflows/opensuse.yml`, run the builder on the
  `collect-runtime` directory for `opensuse-leap-16.0`, keep the RPM CI
  artifact, and release only `dist/*.tar.gz`. Verify the target string,
  the clean-room install step still downloads the RPM artifact, and the
  YAML parses.
- [x] 2.3 In `.github/workflows/opensuse-tumbleweed.yml`, do the same for
  `opensuse-tumbleweed`. Verify the target string, the clean-room install
  step, and the YAML parses.
- [x] 2.4 Add `src/scantpaper/tests/test_release_assets.py` asserting every
  RPM workflow calls the builder with its target, the release step uploads
  only `dist/*.tar.gz`, the tag guard remains, and the existing CI
  artifact names are unchanged. Verify
  `pytest src/scantpaper/tests/test_release_assets.py` and
  `pytest src/scantpaper/tests/test_packaging_opensuse.py` pass.

## 3. Release page text

- [x] 3.1 Add `.github/release-notes.md` with the Downloads section: an
  introduction, a Fedora 43/44 command using a `FEDORA` variable and
  wildcards, a Leap 16.0 command, a Tumbleweed command with
  `--allow-unsigned-rpm`, a note that the `.deb` and `.whl` are single
  files and that Debian and Ubuntu users should prefer apt and the PPA, and
  a link to the README. Verify the file names all four targets and contains
  no full versioned ScantPaper filename.
- [x] 3.2 Add `body_path: .github/release-notes.md` to all five release
  steps in `test.yml`, `deb.yml`, `fedora.yml`, `opensuse.yml` and
  `opensuse-tumbleweed.yml`. Verify each step keeps its
  `github.ref_type == 'tag'` guard.
- [x] 3.3 Extend `src/scantpaper/tests/test_release_assets.py` to assert
  the body file exists, names `fedora-43`, `fedora-44`,
  `opensuse-leap-16.0`, `opensuse-tumbleweed`, `.deb`, `.whl` and
  `--allow-unsigned-rpm`, and that every release step passes `body_path`.
  Verify the test and `test_markdown_line_length.py` pass.

## 4. Documentation and procedure

- [x] 4.1 Update the Fedora, Leap and Tumbleweed sections of `README.md` to
  download the target archive, extract it, and install its RPMs in one
  transaction. Remove the `.lp160.1` selection rule and the individual-RPM
  download wording. Verify the documented names and commands match the
  bundle layout, and the Markdown line-length test passes.
- [x] 4.2 Update `packaging/opensuse/README.md` so the published artifact is
  the target archive containing the `collect-runtime` set, not the
  individual RPMs. Verify no remaining text says the release publishes
  individual RPMs and the build and collect commands still match
  `build.sh`.
- [x] 4.3 Update `release_procedure.md` so a rebuilt tagged release replaces
  one archive per target and the static body needs no edit. Verify the
  dispatch list and replacement step name the same four targets.
- [x] 4.4 Extend `src/scantpaper/tests/test_release_assets.py` to assert the
  README and `packaging/opensuse/README.md` describe the archive workflow
  and no longer tell users to pick Leap by `.lp160.1`. Verify the test
  passes.

## 5. Integration checks

- [x] 5.1 Run `python3 -m pytest`, `ruff check`, `ruff format --check`,
  `ty check .` and `python3 dev/check_test_coverage.py`. Verify all pass,
  coverage stays at or above the configured threshold, and no newly
  unexecuted statements are reported.
- [x] 5.2 Run `openspec validate group-release-assets-by-distro --type
  change`, `openspec validate --specs --strict --no-interactive` and
  `openspec validate --archived --no-interactive`. Verify each reports no
  failures.
- [x] 5.3 Exercise the builder against real Fedora and openSUSE RPM sets and
  verify the archives install in the existing clean-room containers. If a
  full local container run is not available, verify with a dispatched
  workflow run instead.

## Workflow follow-up

- Dispatch the Fedora, Leap, Tumbleweed and Debian workflows with
  `source_ref=vx.x.x` and confirm a rebuilt release replaces one archive
  per target.
- Publish a tag and confirm the release body shows the Downloads section
  and the asset list contains only the planned archives, the `.deb`, the
  `.whl` and the generated source archives.
- Archive the change after the release is verified.
