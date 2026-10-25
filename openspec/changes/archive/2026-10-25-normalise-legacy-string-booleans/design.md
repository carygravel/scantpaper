# Design

## Context

See `proposal.md` - Why for the reporter's symptom and the Perl-era origin of
the empty string.

The relevant load pipeline is in `src/scantpaper/config.py`:

```text
read_config()
  _deserialise_and_migrate()   per-key shape repairs
  _normalise_types()           wrong-type repair
    _coerce_to_type(value, type(DEFAULTS[key]))
      _coerce_bool(...)
  logger.debug(config)
  return config (with config.load_warnings)
```

`_coerce_bool` currently accepts real `bool`, the integers 0 and 1, and the
strings `"true"`, `"false"`, `"0"` and `"1"` (case-insensitively); anything
else yields `None`. `_normalise_types` treats `None` as "cannot be used":
it keeps the raw value, logs a WARNING, and appends a user-visible message.
That message is what `ApplicationWindow._notify_config_load_warnings` shows at
startup. A successful conversion is logged at INFO and is not shown.

`write_config` serialises the in-memory value on quit, so an uncoerced `""` is
written back unchanged and the warning repeats.

Legacy gscan2pdf 2.x configs recorded a Gtk checkbox through
`$button->get_active`. Under older `JSON::PP` releases the false value
serialised as `""` and the true value as `"1"`. The true half is already
accepted by `_coerce_bool`; the false half is the gap.

## Goals / Non-Goals

**Goals:**

- Correct `""` to `False` for every setting whose default is a boolean, using
  the existing normalisation path.
- Keep the correction out of the start-up dialog, log it at INFO, and persist
  the boolean on the next config write.
- Keep every other unrecognised string on the existing warning path.

**Non-Goals:**

- Changing coercion for integer, float, or string settings.
- Accepting additional spellings such as `"yes"`, `"on"`, or whitespace-only
  strings.
- Reinterpreting a non-empty `post_save_hook` as a command and moving it to
  `current_psh`.
- Changing the config schema, defaults, UI, or serialisation format.
- Gating the correction on a config version.

## Decisions

### D1: Extend the bool coercion, not a per-key migration

Add the empty string to the false spellings in `_coerce_bool`. The missing
spelling is a property of the boolean type, not of `post_save_hook`, and the
same Perl code path can leave `""` in any of the 23 bool-default settings. A
dedicated `_migrate_...` step for one key (the pattern used for the legacy
`null` image type) would duplicate the mapping and leave the siblings warning.

Alternatives considered:

- **Per-key migration for `post_save_hook`.** Rejected: fixes the report but
  not the class, and adds a second place that knows how booleans are spelled.
- **Suppress warnings for falsy values.** Rejected: silences the dialog but
  leaves the value typed as `str`, so it is re-emitted and can never be
  repaired.
- **Fall back to the default for any uncoercible bool.** Rejected: masks
  genuinely corrupt values and could silently change a user's setting.

### D2: Keep the accepted spellings narrow

Accept exactly `""` in addition to the existing `"true"`, `"false"`, `"0"` and
`"1"`. `""` is unambiguous: Perl's false stringifies to it, it is already
falsy at every consumption site, and no other meaning has ever been stored for
a boolean setting. `"yes"`, `"no"`, `"on"`, `"off"` and whitespace-only values
are not produced by any known writer and should keep warning so a hand-edited
or corrupt value is not silently guessed at.

Implementation-wise this is a data change to the accepted-value check, not a
new branch: the existing mapping already returns `False` for accepted
false spellings, and the `str` type is already narrowed before the check.

### D3: Correct during `_normalise_types`, with no version gate

The existing normaliser already provides exactly the required observable
behaviour: INFO log, no dialog, in-memory correction, persistence on the next
`write_config`. A separate clause in `_deserialise_and_migrate` would have to
reproduce that logging and ordering.

No version gate is needed because `""` is not a valid bool in any config
version. Gating on `version` would leave version-less or hand-written configs
warning forever, which is the failure mode being fixed.

### D4: No call-site changes

Every consumer already treats `""` as false: boolean tests such as
`if self.settings["post_save_hook"]`, and GTK's `set_active("")`. Replacing it
with `False` is therefore behaviour-preserving; only the type and the warning
change. No UI or save-path code needs to be touched.

## Risks / Trade-offs

- **A user meant something else by `""`.** -> There is no other meaningful
  bool value; the app already acted on it as false. The INFO log keeps the
  correction auditable.
- **Broadening coercion could hide a corrupt config.** -> The whitelist grows
  by exactly one known wire value; all other strings still warn, with a test
  pinning that boundary.
- **A future writer might use `""` for another meaning.** -> No version has,
  and a bool setting has no second meaning to attach to it. If that changes,
  the next migration can disambiguate by version.
- **Downgrade behaviour.** -> Older versions read the corrected `false`
  (JSON boolean) exactly as they read a `""` today, so a downgrade is safe.

## Migration Plan

The correction happens on the first start after upgrade: the value is fixed in
memory and written back as JSON `false` when the user quits. No file surgery,
backup, or user action is required. The config file stays valid JSON
throughout, and older versions remain compatible if the user downgrades.

## Open Questions

None.
