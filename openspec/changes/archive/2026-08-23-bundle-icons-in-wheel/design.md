# Design: Bundle icons inside the Python package for wheel installs

## Context

See proposal.md — Why. Current state: `app.py` resolves icons with
`os.path.join(dirname(__file__), "../icons")`, which only works from a source
checkout, then falls back to `/usr/share/scantpaper/icons`. The wheel ships no
icons (`[tool.setuptools.package-data]` bundles only `app.ui`). The `.deb` does
not use the `/usr/share/scantpaper/icons` fallback at all: `deb.yml` installs
`icons/*` into `/usr/share/icons/` (the hicolor system theme), which GTK resolves
by theme lookup. So distro installs are unaffected by the in-app fallback path.

Key constraint: the wheel installs to a user-level `site-packages` and cannot
write to `/usr/share`, so any system-path approach can never serve wheel users.
The wheel must be self-contained, and the in-app lookup must resolve from the
installed package.

## Goals / Non-Goals

**Goals:**
- Icons are bundled in the wheel and resolve for wheel users.
- Source-checkout and test workflows keep working without a special install.
- Distro (.deb) installs keep installing to the system hicolor theme.
- No new runtime dependency; wheel stays `py3-none-any` with no build step.

**Non-Goals:**
- Not converting icons to a compiled GResource (Option C) — adds a
  `glib-compile-resources` build step to the wheel for no current benefit.
- Not relocating icons to `/usr/share/scantpaper/icons` or changing the hicolor
  theme layout the deb relies on.
- Not changing which icons exist or their theme/name registration.

## Decisions

**Decision 1: Move `icons/` into the package (`git mv icons scantpaper/icons`).**
Single source of truth; dev tree and wheel share the same files; no build-time
copy step. The `icons/hicolor/...` sub-structure is preserved.

**Decision 2: Resolve the icon path from inside the package via `__file__`.**
Replace the `__file__`/`../icons` join with `os.path.dirname(__file__)` joined
against `"icons"`, now that the icons live inside the package at
`scantpaper/icons/`. This resolves correctly in a source checkout
(`python3 scantpaper/app.py`), an editable install, and an installed wheel,
because `__file__` is always the real on-disk path of the module.

`importlib.resources.files("scantpaper")` was rejected: in source-run mode the
repo root is not on `sys.path` and `scantpaper/` has no `__init__.py`, so
`scantpaper` is not importable as a package and that call would raise
`ModuleNotFoundError`. The `__file__`-based path avoids the need for an
`__init__.py` or package-structure changes and is the minimal, robust fix.
If the package structure is ever reorganised (e.g. src layout or a proper
`__init__.py`), revisiting this in favour of `importlib.resources` would be
worth reconsidering.

**Decision 3: Keep a system-path fallback after the packaged lookup.**
Fallback order: packaged icons → `/usr/share/scantpaper/icons` → (implicit)
system hicolor theme. The `/usr/share/scantpaper/icons` branch is currently
dead (no installer writes there), but keeping it preserves behaviour if a
distro chooses that layout. The deb continues to resolve purely via the hicolor
theme, so it needs no runtime code path.

**Decision 4: Update `deb.yml`'s icon install source path.**
Because the icons move, `debian/scantpaper.install`'s `icons/* usr/share/icons/`
must become `scantpaper/icons/* usr/share/icons/`. The destination (system
hicolor theme) is unchanged, preserving the deb's existing theme-lookup
behaviour.

## Risks / Trade-offs

- **[Zipped-wheel installs]** A `__file__`-relative path assumes icons are
  unpacked on disk. PyGObject/Gtk apps cannot realistically run from a zipped
  wheel, and neither source nor normal wheel installs are zipped. → Mitigation:
  accept; if zipped installs ever matter, revisit with
  `importlib.resources`/`as_file()`.
- **[deb.yml regression]** Moving the icons breaks the deb install source path. →
  Mitigation: Decision 4 updates the install line in the same change; verified
  by building/inspecting the deb artifact.
- **[Dead fallback path]** `/usr/share/scantpaper/icons` remains unused. →
  Mitigation: intentional; removes nothing now, keeps distro flexibility. Could
  be deleted in a follow-up if never used.
- **[Test coupling to layout]** Tests reference `app.iconpath` and the `../icons`
  path. → Mitigation: update tests to point at the new in-package location and
  exercise the `importlib.resources` resolution.

## Migration Plan

- `git mv icons scantpaper/icons`.
- Update `app.py` iconpath resolution; keep fallback.
- Add icons glob to `[tool.setuptools.package-data]`.
- Update `deb.yml` install source path to `scantpaper/icons/*`.
- Update tests referencing `app.iconpath` / `../icons`.
- Build a wheel (`pip wheel .` or `python -m build`) and verify the icons are
  listed inside it; install into a scratch venv and confirm `Gtk.IconTheme`
  resolves them.
- Rollback: `git mv` back, revert `app.py`, `pyproject.toml`, `deb.yml`, tests.

## Open Questions

- Whether to drop the now-redundant `/usr/share/scantpaper/icons` fallback
  entirely — deferrable; keeping it is the conservative choice and does not
  change specs or tasks.
