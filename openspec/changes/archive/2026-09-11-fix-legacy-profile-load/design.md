## Context

See proposal.md - Why. The bug is a startup crash caused by pre-v3 gscan2pdf
profiles that are stored backend-only (`{"backend": [...]}` with no
`frontend` key). The profile pipeline is:

```
config.read_config → settings["profile"] → ScanDialog(profiles=...)
  (config.py:271)                  (scan_menu_item_mixins.py:107)
                                                      ↓
                              dialog/scan.py:422 profiles[profile]["frontend"]
                                                      → KeyError
```

Two relevant facts shape the fix:

- `_deserialise_and_migrate` (config.py:317) is the established home for
  config migrations — it already removes undefined profiles (config.py:332-336).
- The `Profile` constructor (scanner/profile.py:20-24) has a combined-dict
  path that currently duplicates a key check. Its callers feed it either
  separate kwargs (dialog) or the well-formed output of `Profile.get()`
  (`default-scan-options`, scan_menu_item_mixins.py:428).

## Goals / Non-Goals

**Goals:**

- The application starts with legacy backend-only profiles in effect, not a crash.
- Every profile loaded by the config layer has both `frontend` and `backend`
  keys before any consumer sees it.
- The `Profile` combined-dict path is self-consistent and cannot key-error.

**Non-Goals:**

- Migrating profile option contents beyond adding the missing `frontend` key
  (existing tuple/dict coercion already lives in `Profile.__init__`).
- Auto-generating default frontend options for legacy profiles.
- Changing how newly created profiles are stored.

## Decisions

### D1: Normalise profiles during config migration (config.py)

Add a step in `_deserialise_and_migrate`, next to the existing "remove
undefined profiles" block, that sets missing profile keys to their defaults:

```python
# normalise legacy pre-v3 profiles that lack a frontend key
if isinstance(config.get("profile"), dict):
    for profile in config["profile"].values():
        if isinstance(profile, dict):
            profile.setdefault("frontend", {})
            profile.setdefault("backend", [])
```

Rationale: one place fixes every downstream consumer and matches the
existing migration pattern. Alternative considered: fixing only
`dialog/scan.py` with `.get()`, which works but leaves the malformed shape
in `settings["profile"]` for any other consumer to trip on.

### D2: Harden the dialog's profile loop (dialog/scan.py:418-425)

Change the two unconditional key lookups to `.get()` so a malformed or
legacy profile can never crash dialog construction:

```python
frontend=profiles[profile].get("frontend", {}),
backend=profiles[profile].get("backend", []),
```

This is defence-in-depth: with D1 in place it is normally a no-op, but keeps
the dialog robust if profiles arrive from a source that did not go through
`read_config`.

### D3: Fix the `Profile` constructor combined-dict branch (scanner/profile.py:20-24)

Current code (with the duplicated check):

```python
if isinstance(frontend, dict):
    if "frontend" in frontend:
        backend = frontend["backend"]
    if "frontend" in frontend:
        frontend = frontend["frontend"]
```

The two checks are identical, so it already works for a combined dict — the
duplicate is a no-op. The naive "typo fix" (`"backend" in frontend` on the
second check) would instead set `frontend = frontend["frontend"]` for a
backend-only legacy dict and **introduce** a KeyError for the exact shape
this change fixes. The safe form collapses to a single check plus a `.get`:

```python
if isinstance(frontend, dict) and "frontend" in frontend:
    backend = frontend.get("backend", [])
    frontend = frontend["frontend"]
```

This preserves both existing behaviours tested in test_03_scanner_profile.py:
a combined dict is split (line 88), and an arbitrary dict without a
`frontend` key remains a pure frontend dict (lines 101-102).

## Risks / Trade-offs

- [D2 and D3 overlap D1, so a future refactor could remove the "wrong" layer
  and regress] → D1 is the primary fix; D2/D3 assertions are covered by
  tests so removal is caught.
- [The backend-only dict is indistinguishable from a frontend dict in the
  `Profile` constructor] → That ambiguity is the reason backend-only legacy
  handling lives in the config migration (D1), which knows the intended
  structure, rather than in `Profile`.
- [Normalisation silently changes the stored config] → This matches existing
  behaviour: the app already rewrites config on exit and removes empty
  profiles on load; backend options are preserved unchanged.