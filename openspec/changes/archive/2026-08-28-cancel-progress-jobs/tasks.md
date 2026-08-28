# Tasks — cancel-progress-jobs

## 1. Thread-side PID registry

- [x] 1.1 Initialize `running_pids` as a `dict` in `Importhread.__init__` (importthread.py:38), matching how `Document.cancel()` and the tests already treat it, and verify a unit test asserts the type and produces an empty registry on a fresh thread
- [x] 1.2 Change `create_pidfile()` (basedocument.py:196) to open pidfiles with `mode="w+t"` and return the readable handle, and verify a unit test can seek(0)+read back a value written to it
- [x] 1.3 Have `exec_command()` (helpers.py:44) call `pidfile.flush()` after writing the spawn pid, and verify `test_helpers.py` covers both the `.write()` call and a flushed/readable pidfile
- [x] 1.4 Register the created pidfile in `self.thread.running_pids` inside `create_pidfile()` (or at its call sites) so every in-flight request owns a registry entry, and verify `test_basedocument.py` asserts the pidfile appears in `running_pids` after creation
- [x] 1.5 Deregister each request's pidfile when its request completes in the thread's request-completion step, and verify a test asserts entries are removed from `running_pids` after a job finishes
- [x] 1.6 Attach the pidfile created in `Document._get_file_info_finished_callback1` (document.py:59) to the `get_file_info` request so info-gathering subprocesses are killable too, and verify the import tests still pass

## 2. Kill loop becomes live

- [x] 2.1 Reimplement `Document.cancel()`'s pid read as `pidfile.seek(0); pidfile.read()` (replacing `slurp`), treating empty/unreadable pids as skip-and-rely-on-flag, and verify the updated `test_cancel` in `test_basedocument.py` passes and asserts killpg is invoked for a populated pidfile
- [x] 2.2 Confirm the `pid == 1` guard and queue-drain/flag/kill ordering in `cancel()` remain correct under the dict registry, and verify a test cancelling with an empty-pid entry does not crash and still sets `thread.cancel`

## 3. Route long-running children through the pidfile path

- [x] 3.1 Convert import-path children (`tiffcp`, `ddjvu`, `djvused`, `pdfimages`, `pdftotext`, `pdfinfo`) from bare `subprocess.run`/`check_output` to pidfile-aware launching, preserving `check=True`/error semantics, and verify the import integration tests (`test_1611_import_tiff`, PDF/DjVu import tests) pass
- [x] 3.2 Convert save-path children (`qpdf`, `tiffcp`, `djvused`, unpaper, user-defined commands, post-save hook) to pidfile-aware launching with equivalent return-code/stderr behavior, and verify `test_1111_save_pdf`, `test_121_save_djvu`, `test_131_save_tiff`, `test_docthread` pass
- [x] 3.3 Confirm no `subprocess.run`/`check_output` remains in `importthread.py` or `savethread.py` for long-running conversions (allow short introspection calls), and verify a lint run flags none

## 4. GUI cancel wiring

- [x] 4.1 Add an optional `cancel_callback` to `Progress` (progress.py), have the `queued()` closure invoke it before the existing `self.hide()`, remove the stale commented `# slist.cancel([pid])`, and verify `test_progress.py` asserts clicking the button invokes the callback and hides the bar
- [x] 4.2 Set `post_process_progress.cancel_callback` (and `_scan_progress` as applicable) in `app_window.py` to call `self.slist.cancel(...)` with appropriate finish/process callbacks, and verify a mocked-window test asserts the callback is wired
- [x] 4.3 Remove the now-resolved `# FIXME: import_files() now returns an array of pids.` at file_menu_mixins.py:245 and the duplicate FIXME in `basedocument.cancel()` (or reword them accurately), and verify `pylint` no longer reports W0511 for those lines

## 5. End-to-end verification

- [x] 5.1 Add an integration test cancelling a bulk multi-file import via the thread API that asserts further files are not imported, already-imported pages remain, and a subsequent save works
- [x] 5.2 Keep/adjust existing `test_cancel_*` save tests to assert the `finished_callback` is not called after cancel and a follow-up export completes (spec: "Application remains usable after cancel")
- [x] 5.3 Run the full suite (`pytest`), `black`, and `pylint`; verify all tests pass, the pylint score is equal or better, and coverage does not drop (AGENTS.md gate)