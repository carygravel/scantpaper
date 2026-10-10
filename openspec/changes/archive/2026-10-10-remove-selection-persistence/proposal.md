## Why

The selection rectangle (the rubber-band box drawn on the image) is persisted to
the user's config file on exit and re-applied to whatever page is loaded on the
next launch. On a fresh document this resurrects a stale, meaningless box that
the user must clear or re-arm before they can work — exactly the redundant
click described in the bug report.

## What Changes

- Stop serialising the selection rectangle to the config file on exit, so it is
  no longer remembered across application launches.
- Stop reading a stored selection back on startup, so no stale selection box is
  drawn over a freshly loaded document.
- Preserve the existing within-session behaviour: the selection still persists
  across page changes and is used by crop, OCR region, etc. throughout a session.

## Capabilities

### Modified Capabilities

- `selection-across-pages`: adds a requirement bounding the selection's
  persistence to the current session — it is cleared at application start rather
  than restored from disk, so a stale box is not re-applied to a freshly opened
  document. Existing within-session page-navigation behaviour is unchanged.

## Impact

- `src/scantpaper/config.py`: `write_config` and `read_config` currently
  serialise/deserialise the `selection` value (config.py:355-364, 497-506). Both
  paths change so the selection is treated as transient.
- `src/scantpaper/config.py`: `DEFAULTS` keeps `"selection": None` so downstream
  code that reads `settings["selection"]` continues to work.
- `src/scantpaper/session_mixins.py`: the page-load re-application of the
  selection (session_mixins.py:303) becomes inert at startup because the value
  is always `None` then.
- `src/scantpaper/app_window.py`: tool-change selection restore
  (app_window.py:641-648) is unaffected — it only acts on a non-None in-session
  selection.
- Existing config files may retain a stale `selection` key; it is simply no
  longer read or rewritten.
- Tests: `test_8_config.py` selection serialisation/deserialisation tests and
  any tests asserting selection survives a config round-trip need updating.
