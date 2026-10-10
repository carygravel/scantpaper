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
1. Prepare the version files. This bumps the version in pyproject.toml, stamps
   the current `changelog.md` section with the release date, and adds the dated
   `<release>` element to [org.scantpaper.desktop.metainfo.xml](org.scantpaper.desktop.metainfo.xml).
   The version is taken from the `(unreleased)` heading in `changelog.md`; the
   same date is written to both the changelog and the metainfo file.
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
1. Tag the release
   ```sh
   git status
   git tag vx.x.x
   git push --tags
   ```
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
