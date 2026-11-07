## Downloads

RPM packages are grouped into one archive per distribution target.
Download the archive for your system, extract it, and install all of its
RPMs in one transaction.

Fedora 43 or 44 uses the `fedora-43` or `fedora-44` archive (set
`FEDORA` to your release):

```sh
FEDORA=43
tar -xf scantpaper-*-fedora-$FEDORA.tar.gz
sudo dnf install scantpaper-*-fedora-$FEDORA/*.rpm
```

openSUSE Leap 16.0 uses the `opensuse-leap-16.0` archive:

```sh
tar -xf scantpaper-*-opensuse-leap-16.0.tar.gz
sudo zypper install --allow-unsigned-rpm \
  scantpaper-*-opensuse-leap-16.0/*.rpm
```

openSUSE Tumbleweed uses the `opensuse-tumbleweed` archive:

```sh
tar -xf scantpaper-*-opensuse-tumbleweed.tar.gz
sudo zypper install --allow-unsigned-rpm \
  scantpaper-*-opensuse-tumbleweed/*.rpm
```

Each archive contains the complete runtime set, a `SHA256SUMS` file and
an `INSTALL.txt`. The `.deb` and `.whl` are single files; Debian sid and
Ubuntu users should prefer apt and the PPA. See the [installation
guide](https://github.com/carygravel/scantpaper#download-installation--removal).
