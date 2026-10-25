# Release procedure:

1. Test scan in lineart, greyscale and colour.
1. New screendump required? Print screen creates screenshot.png in Desktop.
1. Check for upstream translation changes
   ```sh
   python3 dev/check_launchpad.py
   ```
   This reports whether anything moved on
   [Launchpad](https://translations.launchpad.net/scantpaper) since the last
   sync: the template (the message set / `.pot`) and any language whose
   last-changed time is newer than the baseline in
   [po/launchpad-state.json](po/launchpad-state.json). It also reports whether
   the local template is stale relative to the last pot uploaded to Launchpad
   (a `Local pot is stale:` line listing the added and removed strings). The
   scheduled [translations-check workflow](.github/workflows/translations-check.yml)
   runs the same check daily and files one issue when it detects upstream
   changes and a separate one when new strings are ready to upload. A
   "could not determine" result (non-zero exit) means the check could not read
   Launchpad, not that nothing changed, so the download below is still needed.
1. Download new translations (https://translations.launchpad.net/scantpaper)
1. Advance the translation baseline, so the next check compares against the
   state the catalogs were just synced from
   ```sh
   python3 dev/check_launchpad.py --update
   ```
1. Update translators in credits (https://launchpad.net/scantpaper/+topcontributors)
1. Prepare the three version files. This bumps the version in pyproject.toml,
   stamps the current `changelog.md` section with the release date, and adds
   the dated `<release>` element to
   [org.scantpaper.desktop.metainfo.xml](org.scantpaper.desktop.metainfo.xml).
   The version is taken from the `(unreleased)` heading in `changelog.md`; the
   same date is written to both the changelog and the metainfo file. The RPM
   specs are build-time templates and are not changed by this step.
   ```sh
   python3 dev/release.py --dry-run  # preview the changes
   python3 dev/release.py            # write them
   ```
1. Upload .pot
   ```sh
   python3 dev/generate_pot.py
   ```
   After the new template has been uploaded to Launchpad, record its message
   set as the baseline for the local staleness check, so the next run no longer
   reports the pot as stale
   ```sh
   python3 dev/check_launchpad.py --record-pot
   ```
1. Tag the release and push the tag. The tag is what identifies a release:
   the RPM workflows render the spec and source archive from the pushed tag,
   with no release-time spec edit.
   ```sh
   git status
   git tag vx.x.x
   git push origin main --tags
   ```
   RPM builds use `Release: 0.<commit-count>.g<short-sha>%{?dist}`, including
   tagged releases. This keeps every upstream build below a distribution
   package at `Release: 1`, without an `Epoch`. Only builds launched from a tag
   are attached to a GitHub release; branch and pull-request builds are not
   published.
1. Rebuild an already-tagged release. Dispatch the Fedora, openSUSE and
   Debian workflows from `main` with `source_ref=vx.x.x`. The dispatch input
   defaults to `github.sha`; setting it makes the renderer read the version,
   source and commit date from the selected tag instead of `main`. The run is
   a branch run, so its artifacts are not attached automatically; download
   them and replace the release assets manually.
1. The Debian `.deb` attached to the release is built by
   [deb.yml](.github/workflows/deb.yml) from the pushed tag, in the same way.
   Its packaging is maintained in
   [packaging/debian/](packaging/debian/README.md) and rendered into
   `build/deb/`, so the workflow authors no packaging file and the repository
   root stays free of a `debian/` directory. Do not add `/debian/` to
   `.gitignore`: that file ships in the source tarball, where the rule would
   hide newly added files in salsa's own `debian/` directory. The rendered
   version is `<version>-0.<commit-count>.g<short-sha>`, which sorts below the
   distro package at revision `1`. The workflow builds it in a Debian unstable
   container and then runs lintian and autopkgtest on it there; unstable
   provides the `debhelper` the packaging requires and resolves the
   dependencies without the PPA. To reproduce the artifact locally, follow
   `packaging/debian/README.md`.
1. Build package for Debian. Update the salsa repo:
   ```sh
   gbp import-orig --pristine-tar --uscan
   #tox -e signed_sdist
   #sudo sbuild-update -udr sid-amd64-sbuild
   ```
1. Make appropriate updates to debian/changelog
   ```sh
   debuild -S -sa
   # or
   sbuild -sc sid-amd64-sbuild
   debsign .changes
   # then
   lintian -iI --pedantic .changes
   autopkgtest .changes -- unshare --release sid
   # check contents with dpkg-deb --contents
   # test dist sudo dpkg -i scantpaper_x.x.x_all.deb
   dput ftp-master .changes
   ```
1. Push changes to salsa:
   ```sh
   git add -p
   debcommit -r
   git push --set-upstream git@salsa.debian.org:python-team/packages/scantpaper.git : --tags
   ```
1. Build packages for Ubuntu

   Name the release -0~ppa1<release>, where release (https://wiki.ubuntu.com/Releases) is:
   - stonking (until 2027-07)
   - resolute (until 2031-05) - dh13
   - noble (until 2029-06) - dh13
   - jammy (until 2027-06) - dh13, remove override_dh_installman, clear debian/scantpaper.manpages

   ```sh
   debuild -S -sa
   dput gscan2pdf-ppa .changes
   ```

   Watch them [build](https://launchpad.net/~jeffreyratcliffe/+archive).

   Note: when we drop jammy, we can bump target-version & requires-python and
   drop the tomli conditional (;python_version<'3.11')

### When jammy is dropped: modernise GTK4

Until jammy is dropped in 2027-06, the compatibility floor is GTK 4.6 and
PyGObject 3.42 (the versions in Ubuntu 22.04). Code and tests must use only
APIs available there; a newer toolkit API may be used only when it is
detected at runtime and has a working fallback. The `oldest` CI job runs on
Ubuntu 22.04 and enforces this floor.

The GTK3→GTK4 port deliberately kept the already-deprecated GTK4 widgets so
it runs on jammy's GTK 4.6.9. Once jammy (GTK 4.6) is dropped, the CI floor
rises to noble (GTK 4.14), which unlocks GTK4 widgets introduced after 4.6
and lets us clear the deprecations. Each item below becomes available only
after the floor moves; they are independent and can be done one per release.

- Raise the minimum supported distro to noble and drop jammy from the PPA
  build list (and the `oldest` CI job if it is the jammy one).
- Bump `requires-python` / `target-version` and drop the tomli conditional
  (`;python_version<'3.11'`), as noted above.
- Replace `Gtk.Dialog` usage with `Gtk.AlertDialog` / plain `Gtk.Window`
  (deprecated since 4.10).
- Replace `Gtk.ComboBox` / `Gtk.ComboBoxText` with `Gtk.DropDown` +
  `Gtk.StringList` (4.10 / 4.4).
- Replace `Gtk.EntryCompletion` with the list-model completion / `Gtk.DropDown`.
- Replace `Gtk.TreeView` / `Gtk.ListStore` / cell renderers with
  `Gtk.ListView` + `Gtk.ListItemFactory` (or `Gtk.ColumnView`) where a
  columned list is wanted.
- Replace `Gtk.Notebook` with `Gtk.Stack` + `Gtk.StackSwitcher` (or keep
  Notebook if preferred - it still exists, only deprecated).
- Optionally move the custom canvas/imageview rendering from the Cairo
  `set_draw_func` path to the snapshot / `GtkGLArea` API; only if a
  rendering feature requires it.
- Optionally drop the local `graphene.Rect` wrapper (if introduced during
  the port) now that the floor is newer.
- Remove the corresponding `gi.require_version` workarounds introduced to
  stay on 4.6-compatible APIs, and clear any GTK4 deprecation warnings.

A release that ships a GTK4 widget must drop jammy in the same release, so a
jammy user never installs a build that requires a widget its GTK4 cannot
provide.


1. gscan2pdf-announce@lists.sourceforge.net, gscan2pdf-help@lists.sourceforge.net,
   sane-devel@lists.alioth.debian.org
1. To interactively debug in the schroot:
   Duplicate the config file, typically in /etc/schroot/chroot.d/, changing
   the sbuild profile to desktop
   ```sh
   schroot -c sid-amd64-desktop -u root
   apt-get build-dep scantpaper
   su - <user>
   pytest
   ```
