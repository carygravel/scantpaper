# Design

## Context

See `proposal.md` for motivation and `specs/hocr-text-layer/spec.md` for the
behaviour contract.

The current storage and save paths already separate the data this change
needs:

- `page.text` holds the text layer as a JSON bounding-box tree.
- `page.annotations` is a separate column and is not part of the text layer.
- `image.image` holds the page pixels, referenced by `page.image_id`.
- `Page.export_hocr()` serialises the text layer with
  `Bboxtree.to_hocr()`, and the PDF save path already writes that exact
  output as the OCRmyPDF sidecar.
- `do_save_hocr()` concatenates the body of each selected page's
  `export_hocr()` output and writes one header and body. A page with no text
  layer currently contributes only whitespace, so it disappears from the
  combined file.
- `Bboxtree.from_hocr()` parses all `ocr_page` roots but keeps only the
  first one.
- `DocThread._version_page()` clones a page row with a text override, shares
  its image, and preserves annotations and order. `do_set_text()` commits one
  page per call.
- The existing tool dialogs use `Dialog.add_page_range()` and the worker
  callbacks for queued, started, running, finished, error, and cancel
  handling.

The real page 19 hOCR export was checked against the old session: 177 words
with the same ids, boxes, and confidence values, and `import_hocr()` followed
by `export_hocr()` reproduces the file byte for byte.

## Goals / Non-Goals

**Goals:**

- Import one or more hOCR pages into selected or all pages, in order.
- Make combined hOCR exports positionally complete, including empty pages.
- Keep the import atomic, undoable as one action, and cancellable.
- Preserve the text layer exactly as the PDF save path would have serialised
  it.

**Non-Goals:**

- Exporting or importing annotations.
- Matching pages by content fingerprint or filename. Mapping is positional.
- Supporting ALTO, PDF text layers, or other OCR formats.
- Preserving hOCR font metrics that the current exporter does not write.
- Changing how a PDF text layer is generated.

## Decisions

### Add a multi-page hOCR parser rather than splitting the HTML

`Bboxtree.from_hocr_pages()` will parse the document once and return one
`Bboxtree` per `ocr_page` root, keeping the page root even when it has no
children. The existing `from_hocr()` keeps its single-page first-root
behaviour by using the new parser and discarding a first page that has no
text or descendants.

Splitting the raw HTML with a regular expression was rejected: `ocr_page`
elements can nest arbitrarily deep, and a regex would be fragile with
attribute order, quoting, and nested markup. Changing `from_hocr()` to return
a list was rejected because it would break every existing caller.

Keeping the page root for an empty page is what makes geometry validation
possible: the root carries the `0 0 width height` box even when there are no
words.

### Export an empty page box from `Page.export_hocr()`

When a page has no text layer, `Page.export_hocr()` will build a tree with a
single page box at the page's pixel size and serialise that. The existing
header/body concatenation in `do_save_hocr()` then works unchanged: every
selected page contributes exactly one `ocr_page`, and the header is still
written once.

Handling this in `do_save_hocr()` instead was considered. Putting it in
`Page.export_hocr()` keeps the page representation complete for any future
caller and makes the export/import round trip symmetric. The PDF save path
only calls `export_hocr()` for pages with a non-empty text layer, so this
does not change PDF output.

### Validate the whole file before writing anything

`DocThread.do_import_hocr()` will read and parse the file, compare the number
of `ocr_page` roots with the target page count, and compare every root's page
box with the target page's pixel size before it takes an undo snapshot or
writes a row. A mismatch or parse failure calls `request.error()` and leaves
the database untouched.

The page-box comparison allows a one-pixel difference in width and height.
The real `wikimedia.hocr` export has page boxes of `2480 x 3506`, while the
Wikimedia PDF images are `2480 x 3507`; the text boxes all fit within 3506, so
the difference is rounding, not a crop or resize. A larger difference still
fails, which keeps the guard against cropped, rotated, or resampled pages.

This is deliberately stricter than applying pages until one fails. A partial
import would leave the document in a state the user did not ask for, and the
undo history would already contain a step. All-or-nothing matches the
"replace the text layer" contract.

The rejection message must reach the user. `Request.error()` takes an `info`
value and a `status` value, and the application's error callback displays the
`status`. The hOCR import will pass its reason as the status so the error
dialog shows the page count, dimensions, or parse failure instead of an empty
message. A broader fallback in the shared error callback was considered, but
that would change every one-argument error call and is outside this change.

### Apply the import as one undo step in one transaction

After validation, the worker takes one snapshot with `_take_snapshot()`, calls
`_version_page(text=...)` for each target page, and commits once. Empty hOCR
pages pass `text=None`; pages with text pass the parsed JSON. The existing
`_version_page()` already copies `image_id` and `annotations`, so only the
text column changes.

The alternative - the UI calling `set_text()` once per page - would create one
undo step per page and would commit each page separately. It would also make
cancellation partial. The batch method is the same pattern the other
multi-page tools use, but it needs its own transaction because `set_text()`
commits per page.

### Use positional mapping and a page-box guard

Target pages are the selected pages, or all pages, in document order. The
hOCR pages are used in file order. The page-box check rejects a file whose
page geometry differs from the target by more than one pixel, which catches
cropped, rotated, or resampled pages and many wrong-order mistakes while
allowing harmless one-pixel rounding differences.

A content fingerprint in the hOCR was considered and rejected: existing files
do not contain one, and adding one would not help when importing into a
rebuilt session whose image bytes differ. Same-size pages in the wrong order
remain a user-ordering responsibility, documented in the dialog and README.

### Treat an empty hOCR page as an empty text layer

An `ocr_page` with no words or text sets the target page's text layer to
`None`, clearing any existing text. This is the only way to make a source page
that had no OCR round-trip over a target page that has text. It is undoable
with the rest of the import. Skipping empty pages was rejected because it
would silently keep the target's old text and break the positional round trip.

### Add a dedicated import dialog

A new `ImportHocrDialog` will contain a read-only path entry with a Browse
button, the existing page-range frame, and OK/Cancel actions. The menu action
lives under File and is enabled whenever the document has at least one page,
independent of whether any page is selected.

Using the current selection as an implicit "all when nothing is selected"
rule was rejected: a user with a selection could not import into all pages
without clearing the selection. Opening a bare file chooser first and asking
for the page range afterwards was rejected as an extra step.

## Risks / Trade-offs

- **Same-size pages in the wrong order are not detected.** The page-box guard
  only catches geometry differences. Mitigation: the dialog states that pages
  are matched in order, and the README documents that the TIFFs must be
  imported in the old session's page order.
- **The one-pixel tolerance accepts a page cropped or resized by one pixel.**
  The text layer is then off by at most one pixel, which is negligible and
  preferable to rejecting a valid file. A larger crop or resize is still
  rejected.
- **The error reason can be lost if it is passed as `info` rather than
  `status`.** Mitigation: the hOCR import passes the reason as the response
  status and a test asserts that the error dialog receives it.
- **An empty hOCR page clears existing text.** This is intentional for a
  round trip, but could surprise a user importing a partial file. Mitigation:
  the whole import is one undo step, and the spec makes the clearing
  explicit.
- **Old multi-page hOCR files may not contain pages that had no OCR.** The
  new exporter fixes this, but a file saved by an older version can still
  have a page-count mismatch. Mitigation: the error reports both counts, and
  the user can select the pages that the file actually contains or re-export
  from the old session.
- **Annotations are not migrated.** A rebuilt session will not receive the
  old annotation layer. Mitigation: this is an explicit non-goal; the
  reporter's page 19 has no annotations, and the feature is described as
  text-layer import.
- **A cancel during the write phase must roll back.** The write loop is short,
  but a cancellation or database error between `_version_page()` calls could
  otherwise leave a partial action. Mitigation: wrap the write phase in a
  transaction, roll back on any exception or cancellation, and re-raise so the
  request reports cancelled or failed.
- **New translatable strings.** The menu item, dialog labels, and error
  messages need `_()` and a `.pot` refresh. Mitigation: include the
  translation workflow in the tasks and keep the strings short and
  placeholder-based.

## Migration Plan

No database schema change and no data migration are required. Existing
sessions and existing hOCR files continue to load. A user can export hOCR
from an old session, rebuild the session from the original images, and import
the hOCR. Reverting the change removes the menu action and leaves existing
sessions untouched.
