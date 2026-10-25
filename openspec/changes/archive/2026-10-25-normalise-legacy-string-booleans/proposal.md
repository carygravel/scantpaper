# Proposal

## Why

A user upgrading from gscan2pdf 2.x sees this message on every startup:

```text
The setting post_save_hook is '' and cannot be used as bool, so it has been
left unchanged.
```

The message comes from scantpaper's own type normalisation
(`_normalise_types` in `src/scantpaper/config.py`): `DEFAULTS` declares
`post_save_hook` as a bool, the config file holds the empty string, and
`_coerce_bool("")` cannot classify it, so the raw value is kept and reported.
Because the value is never repaired, `write_config` re-emits `""` on quit and
the dialog returns on the next launch, indefinitely.

The empty string is not user error. It is how older Perl-era configs recorded
Glib boolean false: gscan2pdf 2.x assigned `$pshbutton->get_active` into the
setting, and `JSON::PP` releases before ~2.97001 (for example 2.27300 shipped
with Perl 5.24) serialised that value as `""`. The true form from the same
path is `"1"`, which `_coerce_bool` already accepts and silently converts, so
only the false half still warns. The repo's own legacy logs show the surviving
true half (`'cache options': '1'`).

The app already behaves correctly for `""` because it is falsy: the hook stays
off and GTK treats the value as an unticked box. Only the typing and the
warning are wrong, and the documented `config-loading` policy already says a
value that can be made usable must be corrected in the log rather than shown
to the user. This is a missed case of that policy, not a new feature.

## What Changes

- Treat the empty string as a lossless boolean false in `_coerce_bool`, so any
  bool-default setting holding a Perl-era `""` is corrected instead of
  reported.
- Log the correction at INFO through the existing `_normalise_types` path and
  persist the corrected `false` on the next config write, so the warning
  cannot recur.
- Apply the correction to every bool-default setting, not only
  `post_save_hook`, because the same Perl code path can leave `""` in
  `close_dialog_on_save`, `OCR on scan`, `unpaper on scan` and the other
  boolean preferences.
- Keep the warning for unrecognised non-empty strings, and do not reinterpret
  a non-empty `post_save_hook` as a stored command.
- Do not version-gate the correction: an empty string is never a valid bool in
  any config version.

## Capabilities

### New Capabilities

- none

### Modified Capabilities

- `config-loading`: extend the wrong-value-type normalisation so that
  stringified legacy booleans from gscan2pdf 2.x, including the empty string
  for false, are converted losslessly at load time with an INFO log, no
  start-up message, and a corrected value on the next write.

## Impact

- `src/scantpaper/config.py`: `_coerce_bool` (no new module, dependency, or
  configuration key).
- `src/scantpaper/tests/test_8_config.py`: coercion unit test plus load,
  warning, log and round-trip tests.
- `openspec/specs/config-loading/spec.md`: one requirement and its scenarios.
- `changelog.md`: one user-visible bullet.
- No API, data-model, or serialisation change: `scantpaperrc` stays valid JSON
  and a corrected value is written as `false`.
