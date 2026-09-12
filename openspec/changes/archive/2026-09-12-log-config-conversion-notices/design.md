## Context

`_normalise_types` in `src/scantpaper/config.py` appends a `load_warnings`
entry for every coerced setting, both successful conversions and failures.
`app_window._read_config` stashes `settings.load_warnings` and
`_notify_config_load_warnings` shows every entry in a startup dialog. The
rescue notices from a failed parse follow the same path, but only the parse
failure itself is logged (`logger.exception`); none of the follow-on notices
are. Logging defaults to WARNING on stderr and DEBUG when a `--log` file is
given (`src/scantpaper/app.py`).

## Goals / Non-Goals

**Goals:**
- Route lossless type conversions to the log only (info level), never the dialog.
- Keep genuinely actionable messages (rescue notices, values left unchanged) in
  the dialog and additionally write them to the log.
- Preserve the existing quit-time write guard: it defers writes whenever
  `load_warnings` is non-empty, but a parseable config that only needs type
  normalisation should no longer defer the write.

**Non-Goals:**
- Not changing which coercions are considered lossless (`_coerce_*` helpers
  already encode that by returning a usable value vs. `None`).
- Not changing the salvage algorithm or backup behaviour from
  `resilient-config-loading`.
- Not translating log-only strings (logs are not user-facing localised output).

## Decisions

**1. `load_warnings` (dialog) vs. `logger` (log) split in `_normalise_types`.**
The existing `_coerce_*` return value already distinguishes the two outcomes:
a non-`None` result is a lossless conversion, `None` means the value cannot be
made usable and stays raw.
- Success → `logger.info("The setting %s is %r and has been converted to %r.")`
  in English (log-only, so no `_()`), and no `load_warnings` append.
- Failure → keep the translated `_()` warning in `load_warnings` (dialog) and
  also `logger.warning()` it.

*Alternatives considered:* showing a single aggregated dialog line listing all
converted keys. Rejected as still unactionable. *Alternative:* dropping the
messages entirely. Rejected because the type mismatch is worth diagnosing in
logs.

**2. Rescue notices also logged.**
In the `JSONDecodeError` branch, build the translated notice, append it to
`load_warnings` as today, and additionally emit it with `logger.warning()` so
the dialog and log stay consistent. The pre-existing `logger.exception`
already captures the parse error itself.

**3. Severity selection.**
Lossless conversions use INFO because the value is corrected automatically and
the main effect is observability; with no `--log` file, stderr stays quiet for
them (default WARNING), which matches the user's "not useful" framing. Failures
and rescue notices use WARNING so they surface even without a log file and
always reach the dialog.

**4. No change to dialog plumbing.**
`_notify_config_load_warnings`, the `_config_load_warnings` stash, and the
`_can_quit` guard stay as-is. The desired dialog filtering is achieved purely
by what config.py puts into `load_warnings`. A parseable-but-wrong-typed config
now yields an empty `load_warnings`, so no dialog shows and the quit-time write
is no longer deferred for that case.

## Risks / Trade-offs

- **Conversions invisible without a `--log` file** → acceptable: they are
  unactionable for the user; a log file or WARNING-level stderr still shows the
  actionable notices.
- **`load_warnings == []` no longer implies "nothing odd happened"** → the log
  now carries the conversion trail, so diagnostics remain available; tests
  assert on the log via `caplog`.
- **Translations**: removing `_()` from the success string drops it from the
  next generated `.pot`; po files are only touched at release via the standard
  workflow (AGENTS.md), so no manual edit.