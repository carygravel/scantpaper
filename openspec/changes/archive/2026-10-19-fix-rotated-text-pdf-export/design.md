## Context

See proposal.md - Why. The saved text layer is produced by
`Page.export_hocr()` (`page.py:252`), which serialises the flat bbox tree in
`page.text_layer` through `Bboxtree.to_hocr()` (`bboxtree.py:327`) and hands
the result to OCRmyPDF (`savethread.py:186`). OCRmyPDF's hOCR parser reads
`textangle` only from line-level elements (`ocr_line`, `ocr_header`,
`ocr_footer`, `ocr_caption`); a `textangle` on a word is ignored. The current
export keeps each slice's local angle on the slice, so a manually rotated word
is invisible to OCRmyPDF and is rendered horizontally, with the line height
driving an oversized font.

The layer's stored JSON (`canvas.Bbox`) is a separate format. It records local
angles so the editor can compose them through `accumulated_textangle()`
(`canvas.py:1312`). Export must not change that storage; only the hOCR handed
to OCRmyPDF and written by "Save as hOCR" is affected.

`_hocr_with_containers()` (`bboxtree.py:668`) rebuilds a nested tree from the
flat list and calls `_ensure_hocr_containers()` (`bboxtree.py:701`), which
wraps bare words in a synthetic `ocr_par`/`ocr_line` but copies no angle.
Existing line-like nodes are left untouched. `_group_words_into_lines()`
(`bboxtree.py:738`) groups by vertical position only, so it can also merge
words of different orientations into one line.

## Goals / Non-Goals

**Goals:**

- Make the exported hOCR self-describing for renderers: every rendered word
  gets its effective (accumulated) angle on the line-like container that
  OCRmyPDF reads.
- Cover words directly under a page, words in a synthetic line, words in an
  existing line with a matching angle, and words in an existing line with a
  different angle.
- Keep `page.text_layer` JSON, the canvas, undo/redo, and copy/paste
  untouched.
- Add regression tests that fail on the current export and pass after it.

**Non-Goals:**

- Rotation-aware PDF import. `pdftotext -bbox` cannot report direction, and
  replacing the extractor is a separate change (see proposal.md).
- Working around the OCRmyPDF 17.10 issue where a rotated word's length is
  scaled by the short side of its AABB. The test asserts orientation, not
  span, and the issue should be tracked upstream.
- Arbitrary (non-90-degree) angles or rotating bounding-box geometry. The
  editor and hOCR model only carry a text angle.

## Decisions

### 1. Canonicalise angles on line-like elements at export time

Add a normalisation pass to `bboxtree.py` that runs after
`_ensure_hocr_containers()` and before `_flatten_nested()`.

```
before (flat -> nested)                  after normalisation

page textangle=0                         page
└── para                                 └── para
    └── line (no angle)                      └── line textangle=90
        └── word textangle=90                    └── word (no angle)
```

The pass walks the nested tree carrying the sum of ancestor angles. For each
word it computes `effective = (ancestors + own) % 360`. On a line-like node it
sets the line's `textangle` to the effective angle of its words, then removes
`textangle` from the words. On non-line ancestors it recurses first, then
removes its own `textangle`.

Rationale: OCRmyPDF (>= 16.10) applies exactly one line angle, and hOCR
renderers generally do not inherit `textangle` from ancestors. Folding the
accumulated angle onto the line and clearing it elsewhere means the angle is
applied once by every consumer, and a later re-import through
`Bboxtree.from_hocr()` still composes correctly because `accumulated_textangle`
now walks a chain with a single angle.

Alternatives considered:

- Keep ancestor and word angles and add an effective angle to the line. This
  double-counts on hOCR re-import and leaves contradictory data in the file.
- Change `Canvas.Bbox.to_hocr()` to emit accumulated angles. That serialiser
  feeds `page.text_layer`; changing it would change the stored JSON and the
  editor's semantics. Export-time normalisation keeps the storage contract
  intact.

### 2. Split line-like nodes whose words have different effective angles

On a line-like node with more than one effective word angle, group the words
by effective angle, preserving their source order, and replace the node in its
parent with one line-like node per group. Each new node gets the union bbox of
its words and the group's effective angle.

The group whose angle equals the original node's effective angle keeps the
original type and metadata (`id`, `baseline`, font metrics). Additional groups
become `line` nodes with no `id` and no `baseline`, so the renderer derives a
baseline from font metrics. IDs therefore stay unique.

Rationale: hOCR carries at most one angle per line. Splitting is the smallest
structure that can represent a manually added vertical word inside an existing
horizontal OCR line without disturbing the other words on that line.

`_group_words_into_lines()` is not changed. It may still group words of
different angles by position for a freshly created synthetic line, but the
split pass separates them afterwards. This keeps angle handling in one place
and works for existing lines too.

### 3. Raise the OCRmyPDF floor to 16.10.0

hOCR `textangle` support was added in OCRmyPDF 16.10.0. Older releases ignore
the attribute no matter where it is written. Raise `pyproject.toml` and the
generated Debian control file to `ocrmypdf>=16.10.0`. The PPA ships 16.13.0
for jammy and noble, and the openSUSE Leap 16 build already uses 16.11.1, so
every supported target can meet the floor.

Alternative: keep the old floor and emit a warning when
`ocrmypdf.__version__` is too old. That would leave a known-broken save path
for the lowest supported release, so it is rejected.

### 4. Test the transform and the saved PDF separately

- `test_75_bboxtree.py`: assert a bare rotated word yields a synthetic
  `ocr_line` with `textangle 90`; assert a mixed-angle line is split into two
  lines; assert an ancestor angle lands on the line exactly once; assert
  unrotated output is unchanged.
- `test_1111_save_pdf.py`: set a text layer with a horizontal word and a
  vertical word, save a PDF, and assert the PDF content stream contains a
  rotated text matrix. Parse the decoded page content stream with `pikepdf`
  (already a direct dependency) and look for a `Tm` whose off-diagonal
  entries are non-zero, which both the 16.x and 17.x renderers emit for
  rotated text. Also assert the plain text extraction still contains both
  words. A horizontal-only control case asserts no rotated `Tm` appears.
- No OCR is involved in either test: the text layer is supplied as a fixture,
  so the image content is irrelevant. This keeps the tests deterministic.

The test does not assert the rendered word span, because of the OCRmyPDF
17.10 regression above.

## Risks / Trade-offs

- [A renderer other than OCRmyPDF may interpret a line `textangle` differently
  than the word-level storage did.] -> The exported hOCR now matches the shape
  Tesseract itself produces for rotated lines, and
  `Bboxtree.from_hocr()` round-trips it through the same accumulated-angle
  code the editor uses.
- [Splitting a line changes the number of line objects and the text extraction
  order for a mixed-angle line.] -> Words keep their source order within each
  group; only a line that could not have been rendered correctly before is
  split. A test covers a mixed line.
- [Pages with a `textangle` on an ancestor lose that field in the exported
  hOCR.] -> The effective angle moves to the line, which is the only place a
  renderer reads. The stored JSON still carries the ancestor angle, so the
  editor and an hOCR re-import both show the same rotation.
- [The OCRmyPDF 17.10 span regression makes rotated text look short on that
  release.] -> The change still fixes the orientation; the regression is
  upstream and should be reported. Tests assert orientation only.

## Migration Plan

No data migration: the SQLite schema and `page.text_layer` JSON are unchanged,
and existing sessions load as before. The OCRmyPDF floor is enforced at
install time. Rollback is a revert of the export normalisation and the
dependency floor; sessions and saved output remain valid either way.

## Open Questions

None.
