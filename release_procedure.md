# Release procedure:

1. Test scan in lineart, greyscale and colour.
1. New screendump required? Print screen creates screenshot.png in Desktop.
1. Download new translations (https://translations.launchpad.net/scantpaper)
1. Update translators in credits (https://launchpad.net/scantpaper/+topcontributors)
1. Update version in pyproject.toml
1. Update version and date in `<release>` element in [scantpaper.appdata.xml](scantpaper.appdata.xml)
1. Upload .pot
   ```sh
   python3 dev/generate_pot.py
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
   - jammy (until 2027-06)

   ```sh
   debuild -S -sa
   dput gscan2pdf-ppa .changes
   ```

   Watch them [build](https://launchpad.net/~jeffreyratcliffe/+archive).

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
