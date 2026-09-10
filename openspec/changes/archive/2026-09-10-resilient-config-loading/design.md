## Context

`read_config()` (config.py:157-178) is the single entry point for loading
`~/.config/scantpaperrc` (or `$XDG_CONFIG_HOME/scantpaperrc`). On any
`JSONDecodeError` it renames the whole file to `scantpaperrc.old` and returns an
empty dict, losing every setting. Because `_can_quit()` unconditionally calls
`write_config()` afterwards, the very next quit rewrites defaults over the
rescued state — permanently destroying the user's settings. See proposal.md for
motivation.

`self.settings` is a plain `dict` consumed everywhere (widgets, profile
machinery, `write_config`). `read_config()`'s return type is asserted with `==`
in tests, so the shape needs to stay dict-compatible.

## Goals / Non-Goals

**Goals:**
- Rescue valid keys from an unparseable rc file instead of wiping all settings.
- Preserve the broken original as a backup and never let `write_config`
  silently clobber it.
- Tell the user in the UI when the config could not be read in full.
- Handle wrong-typed values (e.g. `"270"` for an int key) by normalising
  instead of defaulting.
- Stay 100% standard-library: no new Python dependencies.

**Non-Goals:**
- Auto-repairing the JSON (rewriting quotes/commas) — too error-prone.
- A schema/migration system for the rc format.
- Changing the rc file format or the write path for valid files.

## Decisions

### D1: Tolerant load strategy — try, then salvage, never wipe

Order of attempts in `read_config`:

```
json.loads ──► ok ──► deserialise/migrate, return (no warnings)
   │
   ▼ JSONDecodeError
backup file → scantpaperrc.old            (rename, as today)
   │
   ▼
salvage pass: regex-scan file for "key": <value> fragments;
              keep (key ∈ DEFAULTS, value re-parses with json.loads)
   │
   ▼
return rescued dict + warning list
```

Rationale: full-document parsing either works completely or the file is treated
as untrusted, but a poisoned line (hand-edit, encoding glitch) usually leaves the
rest of the key/value pairs intact. A line/`"key": value`-fragment salvage keeps
exactly those. Rejected: third-party permissive parsers (json5/demjson3) — new
runtime dependency for a distro-packaged desktop app, AGENTS.md discourages it;
and auto-repair — silently corrupts values in ways users can't see.

### D2: Load result as a dict subclass, not a signature change

`read_config` returns a `ConfigDict(dict)` that carries a `load_warnings:
list[str]` attribute (empty on success). Rationale: `self.settings`, the
`== example` assertions in test_8_config.py, and `json.dumps` in `write_config`
all keep working unchanged; only the calling site that cares (app_window) reads
the attribute. Alternative considered: returning a `(dict, warnings)` tuple —
rejected, ripples through every caller and test.

### D3: Conservative type normalisation

For each known `DEFAULTS` key on load, if the stored value's type differs from
the default's type, attempt a lossless coercion (int/str/float/bool via the
default's type), else keep the raw value and record a warning. Only affects
keys whose types mismatch — a fully valid file is untouched. `None` defaults
never coerce. Rationale: must satisfy "keep recognised settings with wrong value
types" without surprising users with silent fixes.

### D4: Quit-write must not clobber an unrescued config

Track the failure on `self.settings.load_warnings`. In `_can_quit`
(file_menu_mixins.py:912-951):

- If the load had warnings **and** the user has not been informed, skip the
  `write_config` call (preserving both the rescued in-session settings and the
  on-disk `scantpaperrc.old`).
- Once the warning is acknowledged, normal write proceeds against the live
  settings; `scantpaperrc.old` is never touched by `write_config`.

Rationale: keeps the "don't silently overwrite the original" guarantee while
still persisting the user's *actual* choices from the rescued session.

### D5: Non-blocking user notification

After `show_all()` in `_populate_main_window`, if `load_warnings` is non-empty,
raise a `Gtk.MessageDialog` (INFO) summarising the failure, which keys were
rescued, and the backup path. This re-uses app_window's existing message-dialog
pattern. Rationale: the reporter's symptom depended on the reset being silent;
a visible message makes the failure self-explanatory.

## Risks / Trade-offs

- **Salvage is best-effort** → some settings may still be lost if a value
  doesn't parse; but the rescued keys keep the feature working, the backup
  preserves the original, and the dialog tells the user. Strictly better than
  today's total wipe.
- **Type normalisation could mask a genuinely new-but-valid value type** →
  coercion is only applied against `DEFAULTS` types and always logged; raw
  value kept on failure.
- **Skipping the quit-write in D4 could frustrate users who wanted changes
  saved** → the warning dialog explains the state and a subsequent quit after
  acknowledgement writes normally.
- **`ConfigDict` attribute leaks into `write_config`** (json ignores
  attributes) → harmless; explicit `dict(config)` in write_config if needed.

## Migration Plan

No migration: the rc file format is unchanged; valid files behave identically.
Rollback of the code change restores the old behaviour; `scantpaperrc.old`
backups made by the new version are still standard JSON the old code would read
if renamed back by the user.

## Open Questions

None — the deferred unknowns (exact dialog wording, whether to add a "Restore
backup" button) do not affect the specs, approach, or task breakdown.