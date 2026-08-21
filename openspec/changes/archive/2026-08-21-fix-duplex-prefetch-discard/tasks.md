## 1. Regression tests reproducing #73 (TDD)

- [x] 1.1 Add a scripted fake device handle to test_0821_frontend_image_sane.py implementing brscan5 semantics: `start()` raises "Document feeder out of documents" when no unbuffered frames remain, `snap()` returns the next buffered frame, `cancel()` drops buffered frames and records calls
- [x] 1.2 Test: feeder batch yields both sides of a duplex sheet as 2 pages - verify it fails before the wiring exists (reproduces #73: 1 page, second start raises NO_DOCS)
- [x] 1.3 Test: flatbed batch with cancel-between-pages enabled terminates the session between pages
- [x] 1.4 Test: flatbed batch with cancel-between-pages disabled does not terminate between pages, but does at batch end
- [x] 1.5 Test: reaching the requested page count terminates the session (cancel observed) and discards further buffered frames
- [x] 1.6 Test: mid-batch error reports the error and still terminates the session
- [x] 1.7 Test: user cancel during a page transfer terminates the session

## 2. Core fix in SaneThread

- [x] 2.1 Thread the existing `cancel_between_pages` kwarg through `scan_pages()`, `_scan_pages_finished_callback()` and `scan_page()` into `do_scan_page()`
- [x] 2.2 In `do_scan_page()`, call `snap(no_cancel=not cancel_between_pages, progress=...)`
- [x] 2.3 Enqueue a cancel in each terminal branch of `_scan_pages_finished_callback()` (NO_DOCS end, page count reached) and in the `handler_wrapper()` error branch for `scan_page`, mirroring gscan2pdf Frontend/Image_Sane.pm

## 3. Preference UI fidelity

- [x] 3.1 In preferences.py, make the cancel-between-pages checkbox insensitive when allow-batch-flatbed is disabled, mirroring gscan2pdf bin/gscan2pdf:7064
- [x] 3.2 Test the sensitivity coupling in the preferences test

## 4. Documentation & quality gates

- [x] 4.1 Document the duplex fix in README.md (ADF/duplex scans now import all sides; note that behaviour of multi-page flatbed batches now follows gscan2pdf semantics)
- [x] 4.2 Run `pytest` - all tests pass, coverage not worse
- [x] 4.3 Run `black` and `pylint` - formatting clean, score not worse
