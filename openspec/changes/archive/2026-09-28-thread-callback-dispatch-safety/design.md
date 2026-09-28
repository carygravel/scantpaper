## Context

All long-running work runs on a `BaseThread` worker. The worker pushes
`Response` objects onto a queue and writes one byte to a self-pipe; the GTK
main loop watches that pipe. See `openspec/specs/async-callback-coalescing`
for the one-response-per-iteration contract, and
`openspec/specs/background-job-cancellation` for the cancel semantics. The
pump itself is currently spread over three GLib sources owned by the thread:

```
   _tick        timeout, 200 ms   -> dispatch "running" only
   _drain_one   idle, self-chaining -> dispatch "running", then one response
   _on_readable io watch on the pipe -> monitor(): "running", then one
                                        response, then chain _drain_one
```

Two structural facts shape the fix. First, callbacks are user-supplied and
are documented to be able to re-enter the worker — `SaneThread.cancel()`
calls `send()`, which registers a request. Second, PyGObject removes a GLib
source whose Python callback raises, and no source here is re-armed
independently: the pipe watch is the only thing that drains
`self.responses`, and `_drain_one` is the only thing that chains itself.
So a single escaping exception does not degrade the pump, it ends it.

## Goals / Non-Goals

**Goals:**

- Make the dispatch pass tolerant of registry mutation, since re-entrant
  callbacks are a supported, tested capability rather than a misuse.
- Ensure no exception can remove a GLib source owned by the pump, including
  ones raised by the thread's own glue code rather than by a callback.
- Restore the intended error routing for callbacks invoked without a
  `Response`.

**Non-Goals:**

- Reworking the one-at-a-time coalescing contract or the
  `GLib.idle_add` chaining. It is correct as written.
- Changing how cancel is requested. The `running` stage invoking `cancel()`
  is legitimate and stays supported.
- Making the pump redundant (for example, having `_tick` drain responses as
  a backstop). Once no source can raise, the redundancy buys nothing.

## Decisions

### Iterate a snapshot of the registry

The `running` stage will iterate a snapshot taken before dispatch begins,
rather than the live `dict`.

*Alternatives considered.* Deferring registrations and retirements until the
end of the pass would preserve live-iteration semantics, but it changes when
a newly sent request becomes visible to the dispatcher and pushes ordering
rules into `send()`, for no benefit here. Copying the whole registry per
pass was rejected as unnecessary allocation: the snapshot is only needed for
the `running` stage, which iterates every active request on each tick, and
the registry is small (a handful of entries).

Note that `_execute_stage_callbacks` already re-checks membership before
dispatching, so entries retired by an earlier callback in the same pass are
skipped rather than dispatched against stale state.

### Fix error routing before the dispatch pass, not after

The `running` stage invokes callbacks with no `Response`, so
`_execute_single_callback`'s failure path cannot read `data.request` to build
its log message. That path will be made independent of `data`, so a raising
progress callback reaches `error_callback` with a `status` describing the
failure.

*Why this order.* Had the dispatch-pass fix landed alone, this would have
become a silent no-op: the exception would still escape, but the new guard
would swallow it and log it, hiding a real defect behind the very log line
intended to surface it. Routing first means the guard only ever catches
genuinely unexpected failures.

*Alternatives considered.* Logging a placeholder process name when no
response is available keeps the current structure but leaves the
`error_callback` routing inconsistent between stages. Skipping error routing
entirely for the `running` stage was rejected because the surrounding code
already documents the intent to route. Routing the failure with a
placeholder `request` was rejected for the same reason in stronger form:
`SessionMixins._error_callback` and the import handlers read
`response.request.args` and `response.request.process`, so a `None` request
would make them raise inside the reporting path and the user would still be
told nothing.

*Consequence: the registry carries its request.* Because the response is
gone, the request has to come from somewhere else. `run()` removes the
request from the queue and the handler owns it from then on, so the only
place it is available is `send()`, which builds the registry entry. The
entry will therefore record the request alongside `started`, and the
failure path will read it from there. Entries written by hand elsewhere
read it with `dict.get`, so they keep working. This also makes the log line
name the real process instead of a placeholder, and it lets the routed
error response carry the real `args`, so existing error handlers report the
failing operation as they do for any other error.

### Guard all three pump sources, not just the pipe watch

`_on_readable`, `_drain_one` and `_tick` will each catch and log
exceptions from their dispatch work and return normally.

*Rationale.* Each source is a single point of failure for a different part
of the pump: the pipe watch drains responses, `_drain_one` continues the
drain chain, and `_tick` drives progress for the rest of the request's
life. Guarding only the pipe watch would leave a raising `_drain_one` able
to strand responses with no further pipe traffic to re-arm it. The guard is
`logger.exception`, so a swallowed failure stays visible.

*Alternatives considered.* Installing a `PyGErrorHandler` was rejected: it
is process-global, would change how unrelated GTK callback failures are
reported, and is broader than this problem needs. Re-arming a dead source
from the surviving ones was rejected as more machinery than the guard.

### Rejected: deterministic thread-scheduling tools

Deterministic schedulers such as `blanket` control which *thread* runs
next. That is not the nondeterminism here: all three sources run on the main
thread, and their order is settled inside GLib's C `poll()` and priority
queue, out of reach of a Python-level scheduler. Such tools also require an
effectively single-threaded test, so they cannot drive `GLib.MainLoop.run()`,
which is what these tests are built on. Once the fixes above land, the
outcome no longer depends on the dispatch order at all, so pinning one
interleaving would be pinning a variable the change has already removed.
The underlying technique is still the right one and is used by the new
tests: inject the condition that selects a branch rather than racing to
reach it. Revisit only if free-threaded Python makes thread-level
interleavings themselves significant here.

## Risks / Trade-offs

- [A dispatch pass may now deliver a progress callback to a request that
  reached a terminal state earlier in the same pass] → Membership is
  re-checked before dispatching, so retired requests are skipped.
- [The guard could mask a genuine defect] → Failures are logged with a full
  traceback at `ERROR`, and error routing is fixed first so ordinary
  callback failures are handled rather than guarded.
- [A request whose callback raises repeatedly now logs on every tick while it
  stays active] → Accepted. Such a request is already failing visibly; the
  alternative is a silent stall.
- [`_execute_single_callback` reads `self.callbacks[uid]` more than once, so
  a `before`/`after` callback that retires the *same* request could still
  raise `KeyError`] → Not addressed here. `register_callback` has no
  production callers, so the path is reachable only from tests. Recorded as
  a follow-up rather than widening this change.

## Migration Plan

None. Behaviour-only fix with no API, configuration, or data change. Roll
back is a plain revert.

## Open Questions

None.
