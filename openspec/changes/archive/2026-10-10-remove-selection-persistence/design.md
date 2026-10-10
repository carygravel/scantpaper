## Context

See proposal.md - Why for the motivation. The relevant current state:

- `settings["selection"]` holds the image selection rectangle as a
  `Gdk.Rectangle` (or `None`).
- `config.DEFAULTS` seeds it to `None` (config.py:41).
- `read_config` deserialises a stored selection dict back into a
  `Gdk.Rectangle` (config.py:355-364).
- `write_config` serialises it back to a dict for the JSON config
  (config.py:497-506). `write_config` starts from `output = dict(config)`, so
  the raw `Gdk.Rectangle` would otherwise be un-serialisable by `json.dumps`.
- The restored value is re-applied to every loaded page
  (session_mixins.py:303) and on tool change (app_window.py:641-648), which is
  what resurrects a stale box onto a fresh document.

The goal is to make the selection transient: live only for the current session,
never persisted to disk.

## Goals / Non-Goals

**Goals:**
- Selection rectangle is never written to the config file.
- Selection is never restored from the config file on startup.
- Keep `settings["selection"]` present (as `None` at startup) so existing
  `settings["selection"]` / `.get("selection")` reads keep working unchanged.

**Non-Goals:**
- Changing the within-session behaviour (selection persists across page
  navigation, drives crop/OCR region) — that stays as-is.
- Changing how the selected *tool* (`image_control_tool`) is remembered; that is
  a separate concern and remains persisted.

## Decisions

### Decision: Treat selection as transient in `read_config` / `write_config`

Remove the deserialisation branch in `read_config` (config.py:355-364) and the
serialisation branch in `write_config` (config.py:497-506). In `write_config`,
the selection must be dropped from `output` (e.g.
`output.pop("selection", None)`) so the raw `Gdk.Rectangle` is never handed to
`json.dumps`. In `read_config`, the stale `selection` key must also be popped
(`config.pop("selection", None)`) — otherwise a leftover dict from an older
config would survive into `settings["selection"]` and still be re-applied to a
fresh document.

- **Rationale:** This is the single source of the cross-launch persistence.
  Because `DEFAULTS` seeds `"selection": None`, a fresh launch naturally yields
  `None`, so `session_mixins.py:303` and `app_window.py:641-648` become no-ops at
  startup without further changes. No startup-reset code is needed.
- **Alternative considered:** Keep persistence but explicitly clear the selection
  at startup / on new file. Rejected — it leaves dead config-writing code and a
  second, redundant reset path that can drift out of sync.

### Decision: Keep `"selection": None` in `DEFAULTS`

Do not remove the key from `DEFAULTS`. Downstream code uses both
`settings["selection"]` and `settings.get("selection")`; keeping the key present
avoids introducing `KeyError`s and matches the "no stale selection" default.

## Risks / Trade-offs

- [A `Gdk.Rectangle` left in the config dict would break `json.dumps`] →
  Mitigated by explicitly removing `selection` from `output` in `write_config`.
- [Existing user config files contain a stale `selection` key] → It is simply
  never read or rewritten; it is inert. Optionally it can be dropped when the
  file is next written (already handled by removing it from `output`).
- [Tests assert selection survives a config round-trip] → `test_8_config.py`
  selection test must be updated to assert the selection is now absent/`None`
  after round-trip.

## Migration Plan

No data migration needed. Stale `selection` keys in existing configs are
ignored and not rewritten. Rollback is trivial: restore the two serialisation
branches.

## Open Questions

None.
