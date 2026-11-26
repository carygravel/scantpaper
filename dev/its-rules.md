# Vendored ITS rules

`gtkbuilder.its`/`gtkbuilder.loc` and `metainfo.its`/`metainfo.loc` are copies
of the ITS (internationalization tag set) rules installed on the system.
`dev/generate_pot.py` passes `gtkbuilder.its` to `xgettext --its=` for the
project's Glade/GtkBuilder `.ui` files and `metainfo.its` for the AppStream
metainfo, so it can extract their strings without `intltool` or `itstool`.

## Provenance

- `gtkbuilder.its`/`gtkbuilder.loc`: `/usr/share/gettext/its/`, GNU
  gettext-tools 1.0 (Debian package version `1.0-5`), retrieved 2026-09-27.
- `metainfo.its`/`metainfo.loc`: `/usr/share/gettext/its/`, AppStream 1.0.2,
  retrieved 2026-11-26.

`metainfo.its` and `metainfo.loc` are shipped by AppStream, not by gettext,
even though they install into the same directory. On Debian and Fedora they
come from the `appstream` package; on openSUSE they come from
`AppStream-devel`.

## Do not edit these files

`dev/check_po.py` compares them byte for byte against the copies installed on
the system, so that an upstream change to the rules is noticed rather than
silently diverging. Adding a comment or reformatting either file would make it
differ from upstream by construction, and the drift check would then report a
difference on every run, which is worse than no check at all.

If the rules need changing, change them upstream and re-vendor as below.

## Re-vendoring

```sh
cp /usr/share/gettext/its/gtkbuilder.its dev/gtkbuilder.its
cp /usr/share/gettext/its/gtkbuilder.loc dev/gtkbuilder.loc
cp /usr/share/gettext/its/metainfo.its dev/metainfo.its
cp /usr/share/gettext/its/metainfo.loc dev/metainfo.loc
```

Then update the provenance table above, and check what the new rules extract
before trusting them:

```sh
PYTHONPATH=src python3 dev/generate_pot.py
```

A re-vendor that changes the msgid set changes the strings translators see, so
treat a difference as a change to the translations rather than a mechanical
update. The msgid set is pinned by the tests in
`src/scantpaper/tests/test_po_files.py`, which will fail if it shifts.
