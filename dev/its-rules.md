# Vendored GtkBuilder ITS rules

`gtkbuilder.its` and `gtkbuilder.loc` are copies of the files gettext installs
as part of its ITS (internationalization tag set) rules. `dev/generate_pot.py`
passes `gtkbuilder.its` to `xgettext --its=` so it can extract translatable
strings from the project's Glade/GtkBuilder `.ui` files without needing
`intltool`.

## Provenance

| | |
|---|---|
| Upstream path | `/usr/share/gettext/its/` |
| Taken from | GNU gettext-tools 1.0 (Debian package version `1.0-5`) |
| Retrieved on | 2026-09-27 |

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
```

Then update the provenance table above, and check what the new rules extract
before trusting them:

```sh
python3 dev/generate_pot.py
```

A re-vendor that changes the msgid set changes the strings translators see, so
treat a difference as a change to the translations rather than a mechanical
update. The msgid set is pinned by the tests in
`src/scantpaper/tests/test_po_files.py`, which will fail if it shifts.
