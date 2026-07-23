## Context

`BaseThread` uses a pipe-based notification mechanism (`os.pipe` +
`GLib.io_add_watch`) to wake the main thread when the worker thread has
responses. When the pipe becomes readable, `_on_readable` drains the pipe and
calls `monitor()`. Currently, `monitor()` processes **all** queued responses in a
`while` loop, firing each callback synchronously. This means a burst of N
responses blocks the GUI for the cumulative duration of all N callbacks.

The callbacks involved are `finished_callback`, `error_callback`, `data_callback`,
and any registered before/after hooks. These range from lightweight (updating a
model) to moderately expensive (loading a pixbuf into a GTK image widget).

```
Current flow:
  _on_readable → monitor() → [cb1, cb2, cb3, ..., cbN] all in one tick
```

## Goals / Non-Goals

**Goals:**
- Process at most one response callback per main-loop iteration
- Yield to GLib between callbacks so UI events (repaints, input, animations)
  remain responsive
- Maintain backward compatibility — existing tests and callback contracts must
  continue to work

**Non-Goals:**
- Changing the pipe notification mechanism or request queue
- Modifying callback registration API or the `Request`/`Response` data model
- Optimizing individual callback performance
- Addressing the startup block in `DocThread.__init__()` (separate issue)

## Decisions

### Decision 1: One response per `monitor()` call, chained via `GLib.idle_add`

**Choice:** Change `monitor()` to process one response from the queue, then
schedule itself again via `GLib.idle_add(self.monitor)` if more responses remain.

**Alternatives considered:**

| Approach | How it works | Why rejected |
|----------|-------------|--------------|
| Process all, yield per callback | Wrap each `_execute_single_callback` in `GLib.idle_add` | Breaks the synchronous callback contract — callers expect the callback to have fired when `monitor()` returns |
| Batch coalescing | Deduplicate similar callbacks (e.g., multiple progress updates) | Requires per-callback-type logic, violates the generic design of `BaseThread` |
| `GLib.timeout_add(0, ...)` | Use timeout of 0 instead of idle | Functionally equivalent to `idle_add` but less idiomatic for GLib |
| Track single idle source ID | Only schedule one idle callback at a time, prevent duplicates | Adds complexity with no practical benefit — duplicate idle callbacks are harmless and self-terminating |

**Rationale:** The simple approach (`GLib.idle_add(self.monitor)`) is minimal,
correct, and self-cleaning. Each idle callback processes one response and either
schedules the next or stops. Duplicate scheduling is possible (if `_on_readable`
fires while an idle is pending) but harmless — each callback pops exactly one
response from the queue.

### Decision 2: Keep `monitor()` as the single entry point

**Choice:** `_on_readable` continues to call `monitor()` directly. The idle
chain uses the same `monitor()` method. No new internal methods needed.

**Rationale:** This keeps the change to a single method. The `test_monitor_running_callbacks_on_empty_queue`
test calls `monitor()` directly and expects it to return `GLib.SOURCE_CONTINUE`
and fire running callbacks — both behaviors are preserved.

### Decision 3: `_tick` remains unchanged

**Choice:** `_tick` continues to fire `_execute_callbacks_for_stage("running", None)`
every 200ms for progress reporting. It does not participate in the one-at-a-time
chain.

**Rationale:** Progress callbacks are lightweight and fire independently of
response processing. They iterate over `self.callbacks` (a dict in memory),
not the response queue. Coupling them to the drain chain would add complexity
with no benefit.

## Risks / Trade-offs

- **[Throughput reduction]** — Responses are processed one per main-loop
  iteration instead of all-at-once. For N queued responses, this takes N
  iterations instead of 1. Mitigation: Each iteration is fast (single callback),
  and the main loop runs at ~60fps. Practical impact is negligible for typical
  workloads (tens of responses).

- **[Duplicate idle scheduling]** — If `_on_readable` fires while an idle
  callback is pending, two `monitor()` calls may be scheduled. Mitigation:
  Each call processes exactly one response and the queue is thread-safe. No
  double-processing is possible.

- **[Test compatibility]** — Existing tests call `monitor()` directly and expect
  synchronous behavior. Mitigation: `monitor()` still processes one response and
  returns. Tests with empty queues are unaffected. Tests with queued responses
  will see one response processed (matching the old behavior for single-response
  tests).
