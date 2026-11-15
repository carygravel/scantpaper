# Design

## Context

See `proposal.md` for the incident and motivation.

`VERSION` is resolved at import time in `src/scantpaper/const.py`.
`get_version()` reads `pyproject.toml` at
`Path(__file__).resolve().parents[2]` when that file exists (a source
checkout), otherwise it calls `importlib.metadata.version("scantpaper")`.

`importlib.metadata.version()` returns `metadata["Version"]`. For a
discovered `.dist-info` directory with no `METADATA`, or one whose
`METADATA` has no `Version` header, that value is `None`. It raises
`PackageNotFoundError` only when no matching distribution is found at
all.

The openSUSE specs build `%files` from:

```sh
find %{buildroot} \( -type f -o -type l \) \
    -not -name 'scantpaper.1' \
    -printf '/%%P\n' \
    > %{_builddir}/%{name}-files.list
```

Only files and symlinks are owned, so no directory is owned. A wheel
unpacks to a version-named `scantpaper-<version>.dist-info/` directory.
On upgrade RPM removes the old package's files but leaves that now-empty
directory, and `importlib.metadata` can discover it before the current
one. The released 4.0.4 Leap and Tumbleweed RPMs both list zero
directories; the Fedora RPM lists its `scantpaper-4.0.4.dist-info/`
directory, and dpkg tracks directories for the `.deb`.

`config._version_tuple()` maps a version string with no digits to `()`.
Since `() < (3, 0, 16)`, saving the fallback version as the config
version would make the threshold migration re-run on every start.

## Goals / Non-Goals

**Goals:**

- Version detection always yields a non-empty string and never aborts
  startup.
- The real installed version is recovered when stale metadata shadows
  the current distribution.
- openSUSE RPMs own their version-named metadata directory, so upgrades
  clean it up on both Leap and Tumbleweed.
- Both openSUSE clean-room jobs exercise an installed application with
  stale metadata present.

**Non-Goals:**

- Changing the version source of truth (still `pyproject.toml` or
  installed metadata).
- Adding a package scriptlet that rewrites site-packages on install.
- Changing Fedora or Debian packaging; their packages already own the
  metadata directory.
- Changing the version recorded in already-saved PDFs, hOCR files or
  config files.

## Decisions

### Decision: Version resolution chain in `get_version()`

```text
pyproject.toml at parents[2]
  -> importlib.metadata.version(PROG_NAME)
    -> importlib.metadata.distributions() scan for a valid Version
      -> UNKNOWN_VERSION
```

- Treat a falsy result from `version()` as "no version"; do not assume it
  raises.
- Catch `PackageNotFoundError` and continue to the scan.
- The scan matches a distribution whose normalized `Name` is
  `scantpaper` and returns the first non-empty `Version`. Use
  `metadata.get(...)` rather than subscripting missing headers, which
  avoids the Python 3.14 deprecation warning for implicit `None`.
- Define `UNKNOWN_VERSION = "unknown"` in `const.py`, since it is the
  single fallback shared by version display, config and saved metadata.

Alternatives considered:

- A bare `version() or "unknown"`: fixes the crash but reports "unknown"
  on every affected upgrade and gives unhelpful bug reports. The scan
  keeps the real version.
- A build-generated `_version.py`: reintroduces a second copy of the
  version and build machinery that the metadata approach deliberately
  removed.

### Decision: Unknown versions are not legacy versions

- Keep `_version_tuple(None) == (0,)`: a missing version means an old
  config and its migrations still apply.
- Return a high sentinel such as `sys.maxsize` for a present but
  unparseable string. An unknown version is therefore treated as
  current, not as older than every release.
- The `UNKNOWN_VERSION` string contains no digits, so it naturally takes
  the sentinel path without importing the constant into `config.py`.

Alternatives considered:

- Guard only inside `_migrate_threshold_tool()`. This fixes today's
  migration but leaves the same trap for any future version-keyed
  migration; the tuple helper is the correct single place to define what
  an unparseable version means.

### Decision: Own site-packages directories in the generated file list

- Add a second `find` pass after the existing file pass:

  ```sh
  find %{buildroot} -type d \
      \( -path '%{buildroot}%{python3_sitelib}/*' \
         -o -path '%{buildroot}%{python3_sitearch}/*' \) \
      -printf '/%%P\n' \
      >> %{_builddir}/%{name}-files.list
  ```

- Apply it to all ten specs in `packaging/opensuse/`; the shared
  `build.sh` means Leap and Tumbleweed both inherit it. Pure-Python
  packages only have a `%{python3_sitelib}` tree and compiled packages
  only a `%{python3_sitearch}` tree, so the `-path` filter is a no-op
  for the one that does not exist.
- Filtering to the Python install tree avoids owning shared directories
  such as `/usr`, `/usr/lib`, `/usr/bin` and `/usr/share`.
- Update the `%install` comment that says the list is the single source
  and only files are listed.

Alternatives considered:

- Own every directory under `%{buildroot}`. Simplest, but the package
  would claim shared system directories.
- Add a `%post`/`%posttrans` scriptlet that removes empty stale
  `*.dist-info` directories. It would clean existing installs, but adds
  the first scriptlet to the packaging set; the application fix already
  makes existing stale directories harmless, and the manual cleanup is
  documented. Revisit only if `pip show` confusion becomes a support
  burden.

### Decision: CI guards on both openSUSE targets

- Ownership check in both `.github/workflows/opensuse.yml` and
  `.github/workflows/opensuse-tumbleweed.yml`: for every built RPM,
  assert `rpm -qpl` lists a version-named `*.dist-info/` directory. If
  `rpm -qpl` does not mark directories with a trailing slash on the
  target, use `rpm -qp --qf` with `%{FILEMODES:perms}` or the cpio
  listing instead.
- Stale-metadata check in both clean-room jobs:

  ```sh
  expected=$(scantpaper --version)
  stale=$(python3 -c \
      'import sysconfig; print(sysconfig.get_path("purelib"))')
  mkdir -p "$stale/scantpaper-0.0.0.dist-info"
  actual=$(scantpaper --version)
  test "$actual" = "$expected"
  rmdir "$stale/scantpaper-0.0.0.dist-info"
  ```

  Comparing against the version captured before the stale directory
  exists avoids duplicating the release-version logic, and it still
  rejects both a crash and an "unknown" fallback. The existing tag-build
  equality check continues to assert the exact release version.
- Add a template test in `src/scantpaper/tests/test_packaging_versions.py`
  that every `packaging/opensuse/*.spec` contains the directory-ownership
  `find`. This catches a spec regression before a slow RPM build.

Fedora's packaging already owns its metadata directory, so no packaging
guard is needed there. The application fix is exercised by the unit
tests on every platform. An optional Fedora stale-metadata check is
deferred; it is not needed for the reported defect.

## Risks / Trade-offs

- [Scanning all distributions on the fallback path is slower] -> It runs
  only when `version()` returns no value or raises; normal startup keeps
  the single lookup and is unchanged.
- [Multiple valid `scantpaper` distributions can exist] -> The scan picks
  the first valid one, matching `importlib.metadata`'s own ambiguity. No
  worse than today, and it never crashes.
- [Owning package directories changes uninstall behaviour] -> RPM
  removes a directory only when it is empty, so user data inside it is
  safe.
- [`%{python3_sitelib}`/`%{python3_sitearch}` may not expand on a target]
  -> The macro comes from `python-rpm-macros`, which every spec already
  requires; the `-path` filter is a no-op for a missing tree. The CI
  ownership check verifies the result.
- [Existing stale directories survive the first fixed upgrade] -> The
  application recovers the real version, so startup and `--version` are
  correct; only `pip show` can remain confused. The README documents the
  one-line `rmdir` cleanup.
- [A saved config can hold `"version": "unknown"`] -> The tuple sentinel
  prevents re-running migrations. Any future version-keyed migration
  must use `_version_tuple()`, not string comparison.

## Migration Plan

- Ship the application fix and the packaging fix in the same release.
  Existing stale directories become harmless as soon as the application
  fix is installed; the packaging fix makes the next upgrade remove its
  own metadata directory.
- No data migration is required. The only persistent change is that a
  config may now record `"version": "unknown"`; the sentinel makes that
  safe.
- Rollback: reverting to an older application with `"version":
  "unknown"` saved would re-run the threshold migration on each start.
  Fix the metadata or run `scantpaper` from the fixed build before
  rolling back.

## Open Questions

- Whether to add a `%post` cleanup for already-stale directories and
  mirror the stale-metadata check on Fedora. Both are deferrable and do
  not change the specs, the approach or the task breakdown.
