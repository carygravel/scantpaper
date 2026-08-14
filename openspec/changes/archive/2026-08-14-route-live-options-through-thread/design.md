## Context

`Options` is a plain-Python snapshot of a device's **descriptors** (built once from
`SaneDev.get_options()`), used by the GTK-thread dialog for geometry/source/duplex
logic and by the test suite without any hardware. Live **value** reads are a
different concern: they must reach the `SaneDev`, which lives in the `SaneThread`
worker thread (`frontend/image_sane.py:31`). The intended channel is
`self.thread.send("get_option", name)` → queue → `do_get_option` in the worker
(`image_sane.py:107-110`).

Today that channel is bypassed: `dialog/scan.py` reads `self.thread.device_handle`
directly from the GTK thread (`options.val(...self.thread.device_handle)` at
`675-679`/`1345`, bare `.page_height` at `884-906`, `getattr(...device_handle...)`
at `751`/`1255`). `Options.val` is just `getattr(device_handle, name.replace("-","_"))`,
a duplicate of `do_get_option`. So live reads are both redundant and thread-unsafe.

See proposal.md - Why for motivation.

## Goals / Non-Goals

**Goals:**
- Route every live option read through the worker thread; the GTK thread must
  never touch `SaneDev` directly.
- Keep call-site semantics **synchronous** (callers expect a value immediately),
  so the change is localized and does not cascade into async refactors.
- Delete `Options.val`; make `Options.flatbed_selected` take a value getter rather
  than a raw device handle.

**Non-Goals:**
- Changing the `Options` descriptor snapshot, `by_name`, `parse_geometry`,
  `can_duplex`, `supports_paper`, or `num_options`.
- Converting call sites to async/callback style.
- Removing the empty `Options([])` placeholder or the GObject subclass (separate
  changes).

## Decisions

**D1 — Synchronous `get_option(name)` on `SaneThread`, signaled by the worker.**
Add `SaneThread.get_option(name)` (main-thread API) that sends the request and
blocks on a `threading.Event`. The event is **set inside the worker thread**, not
by the main-loop response callback. Rationale: `BaseThread` drains
`self.responses` from the GLib main loop (`basethread.py:_drain_one`); if the
main thread blocked on that shared queue while waiting for a response, the main
loop that drains it would be stalled → deadlock. Signaling from the worker
directly (via a holder + Event passed through `request.args`) avoids the shared
queue entirely. Alternative considered: reusing the async `finished_callback`
path — rejected because the callback runs on the blocked main loop.

**D2 — Separate worker method `do_get_option_blocking`.**
Keep `do_get_option` (async, returns via `request.finished`) untouched for any
existing/external async callers. Add `do_get_option_blocking(self, request)` that
reads `getattr(self.device_handle, name.replace("-", "_"))` **in the worker** and
stores the result + sets the Event. This confines all `_sane` calls to the worker.

**D3 — Delete `Options.val`; `flatbed_selected(get_value)`.**
`flatbed_selected(self, get_value)` receives a callable returning the live value
for a name; internally `get_value(self.source.name)`. Callers pass
`self.thread.get_option`. Removes the duplicate and the raw-handle coupling.

**D4 — Keep hyphenated names at call sites.**
`do_get_option`/`do_get_option_blocking` already do `name.replace("-", "_")`, so
callers keep passing `"tl-x"`, `"page-height"`, etc. No rename churn.

**D5 — Guard before calling.**
Preserve the existing `if self.thread.device_handle is None: return` guards
(`scan.py:1234-1237`) ahead of `get_option` calls so a closed device fails fast
instead of blocking on the Event.

## Risks / Trade-offs

- **[Main-thread block]** `get_option` blocks the GTK loop until the worker
  replies. Acceptable: identical to today's synchronous `getattr`, and SANE value
  reads are fast. Mitigation: `ev.wait(timeout)` with a sane timeout; on timeout
  raise/return `None` rather than hang.
- **[Signature change]** `flatbed_selected` now takes a callable, not a handle.
  Mitigation: update the few call sites + their tests (pass `self.thread.get_option`).
- **[Test churn]** Many `test_06*/test_0610*` suites mock `self.thread.device_handle`
  and `Options.val`. Mitigation: switch mocks to `self.thread.get_option`; keep
  `Options` constructible from plain tuples (unchanged) so the bulk of tests are
  unaffected.
