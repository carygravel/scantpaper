## Context

See proposal.md — Why: running a long-lived GUI tool (e.g. GIMP) on several
selected pages currently forces one tool instance per page, sequentially.

Today a user-defined tool (UDT) run is strictly per-page:

- `tools_menu_mixins.user_defined_dialog()` loops over pages and enqueues one
  `user_defined` request per page.
- A single worker thread (`basethread.BaseThread.run`) pulls one request at a
  time and calls `savethread.do_user_defined()`, which blocks on
  `exec_command_run()` (`helpers.py`) until the tool process exits.
- Copy-back happens inside the same request: `%o` (or the `%i` working copy)
  is read and `replace_page()` swaps it in, preserving resolution, text layer,
  and saved-state.

Constraints that shape this design:

- The worker thread is serial; callbacks are per-request and feed a
  lifecycle progress bar (`queued`/`started`/`running`/`finished`).
- GUI editors like GIMP are single-instance on Linux: a second `gimp %i`
  invocation hands the files to the running instance and exits immediately.
- Copy-back is only trustworthy "after the process exits", so the contract is
  spawn → wait → diff files → replace.

## Goals / Non-Goals

**Goals:**

- One checkbox in the UDT dialog switches to batch mode: all selected pages
  are passed to a single tool invocation (`gimp %i` opens them all at once).
- Wait for that one process, then replace exactly the pages whose working file
  changed; leave unchanged pages untouched; preserve order.
- Single error / "nothing modified" message per batch; batch is one progress
  job and is cancellable.
- Per-page mode (the default) behaves exactly as today, including `%o`.

**Non-Goals:**

- Tools that produce a single multi-page output from many inputs (`%o` as a
  collected PDF/TIFF).
- Tools that reorder, add, or delete pages.
- Fixing the latent race when a GUI tool is already running; behaviour is
  unchanged and the message should hint at it.

## Decisions

### 1. Batch is one request carrying a list of pages — not parallel workers

A batch becomes a single `user_defined` request whose args carry a list of
`(page_id, working_path)` pairs. The serial worker runs the whole batch in one
`do_user_defined()` call: one spawn, one wait, then copy-back for each entry.

- **Why:** keeps the thread architecture and progress model untouched; a batch
  is naturally "one job". No locking, no re-entrancy, no ordering problems.
- **Alternative rejected:** a pool of concurrent workers, one per page. Besides
  touching the threading core, it is actively harmful for the requested use
  case — 4 of 5 concurrent `gimp` spawns would hand off to the running
  instance and exit, so their `%o` files are never produced.

### 2. `%i` expands to the full list; `%o` is rejected in batch mode

In batch mode `re.sub(r"%i", " ".join(paths), command)` substitutes all
working-file paths. A command containing `%o` is invalid for batch (one single
output cannot collect N pages) and is refused up front in the dialog and again
in `do_user_defined`, with an error naming the tool.

- **Why:** "open all at once" is precisely a multi-input, per-file-output
  workflow; `gimp file1.png ... fileN.png` opens each file in its own window in
  a single instance.

### 3. Per-page working files with a pre-run content snapshot

For each page, create a temp working file (a copy of the page image, as the
existing no-`%o` path already does) and record a digest of its bytes. After the
process exits, replace the page for every working file whose digest changed.

- **Why:** distinguishes "the user edited this one" from "this one was just
  touched" in a mixed batch, which is exactly the spec'd behaviour
  (modified files replace, unmodified ones stay).
- **Alternative considered:** trusting mtime alone — racy on fast filesystems
  with second (or sub-second) granularity, and tools like GIMP may not touch
  mtime if unchanged. A bytes digest is simple and exact.
- **Trade-off accepted:** a tool that re-writes identical bytes will be treated
  as "modified" and swap the page with semantically identical content; harmless.

### 4. Copy-back reuses the existing per-page replacement path

Each replaced page goes through the same code the single-page flow uses today
(`savethread.py:648-670`): load image, build a new `Page` with the old page's
resolution and text layer, `replace_page()`, and emit a `data` response of type
`page` with `replace=<id>`. `data_callback`/`_display_callback` therefore keep
working unchanged for batch, one response per replaced page.

- **Why:** preserves the tested properties (resolution, text layer, page
  position, saved-state) without inventing a parallel mechanism.

### 5. Progress and cancellation come for free from the single-request model

The batch request flows through the normal `queued` → `started` → `running` →
`finished` lifecycle, so the existing progress bar shows it as one job (`Process
1 of 1 (user_defined)`). Cancellation reuses the pidfile registry +
`check_cancelled()` machinery that already kills the spawned process group;
on cancel, no copy-back runs.

### 6. Dialog: a per-use checkbox, verified up front

`user_defined_dialog()` gains `"Process selected pages at once"` (default
unchecked). On apply: if checked and the selected command contains `%o`, show
an error dialog and do not start. Otherwise a single batched
`slist.user_defined(pages=[...], command=...)` replaces the per-page loop.

- **Why:** batch is a property of a single run, not a global preference, so no
  config/`settings` change is needed.
- **Non-goal:** tools that only make sense per-page (e.g. deskew). Users select
  batch deliberately; the checkbox is per run.

## Risks / Trade-offs

- [A GUI tool is already running when batch starts (e.g. GIMP open on other
  work)] → the invocation hands off and exits immediately, no files change,
  batch reports "no pages modified". Mitigation: the message wording explains
  a running tool instance may have swallowed the launch, matching reality
  rather than pretending success.
- [Tool rewrites files byte-identically] → pages are swapped with identical
  content and the document is marked unsaved. Mitigation: acceptable; content
  is unchanged for the user.
- [Huge selections open many windows at once] → user-controlled via the
  checkbox; no artificial cap.
- [`%o` in batch mode silently misbehaves] → both dialog and worker validate
  and refuse, so the failure is loud, not silent.

## Migration Plan

No schema, config, or dependency changes. Per-page behaviour and the existing
`gimp %i` default are untouched. Batch is additive and default-off; reverting
is simply not using it.

## Open Questions

None blocking. Batch-of-one is identical to per-page and needs no special
handling.