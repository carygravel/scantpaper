## Purpose

Defines how page numbers and page order are assigned and maintained in the
document model: page numbers are always consecutive 1..n and derived from
position, and new pages (from scanning or editing) are inserted positionally.

## Requirements

### Requirement: Page numbers are always consecutive
The displayed page number SHALL always equal the page's 1-based position in
the document. After any operation that adds, removes, or reorders pages, page
numbers SHALL be re-derived from the new positions so that numbers are exactly
1..n with no gaps and no duplicates.

#### Scenario: Deleting a page renumbers the remainder
- **WHEN** a page is deleted from a document with pages 1..5
- **THEN** the remaining pages SHALL be renumbered 1..4 consecutively

#### Scenario: Inserting a page renumbers subsequent pages
- **WHEN** a page is inserted after position 2 in a 5-page document
- **THEN** the new page SHALL be numbered 3 and the former pages 3..5 SHALL be
  renumbered 4..6

#### Scenario: Page numbers match positions after reordering
- **WHEN** pages are reordered by drag-and-drop
- **THEN** every page SHALL be renumbered so that number equals position in the
  new order

### Requirement: Page number is derived, not stored
The page number SHALL be derived from the page's position when displayed. No
page number SHALL be persisted in document storage.

#### Scenario: Session stores order but no numbers
- **WHEN** a session is saved
- **THEN** the stored document SHALL contain page ordering information and SHALL
  NOT contain page numbers

### Requirement: Single-sided scanning appends
Single-sided basic scanning SHALL append each new page after the last page.

#### Scenario: Scanning into an empty document
- **WHEN** single-sided pages are scanned into an empty document
- **THEN** the pages SHALL be numbered 1, 2, ..., n in scan order

#### Scenario: Scanning into an existing document
- **WHEN** single-sided pages are scanned into a document that already has n
  pages
- **THEN** the new pages SHALL be numbered n+1, n+2, ..., n+m in scan order

### Requirement: Double-sided scanning interleaves reverse pages
Basic double-sided scanning SHALL append the facing pages 1..n and then place
each scanned reverse page immediately after the front of the same sheet, so
that page numbers remain consecutive after every scan and the final order
alternates front/back of each sheet.

#### Scenario: Reverse pass interleaves behind each front
- **WHEN** a double-sided document of n sheets is scanned, facing first and then
  reverse
- **THEN** each scanned back SHALL be placed immediately after the front of the
  same sheet
- **AND** the final order SHALL be front1, back1, front2, back2, ..., frontn,
  backn
- **AND** page numbers SHALL be consecutive 1..2n at every point during the
  reverse pass

#### Scenario: Saving during the reverse pass preserves order
- **WHEN** the document is saved after only some reverse pages have been scanned
- **THEN** the saved pages SHALL be in the correct interleaved partial order and
  SHALL NOT have backs clustered after all fronts

### Requirement: Duplex rotation follows the side being scanned
The rotation applied to a scanned page SHALL be chosen from the "side to scan"
setting: facing pages use the facing rotation and reverse pages use the reverse
rotation. Page-number parity SHALL NOT influence rotation.

#### Scenario: Reverse pages rotate by the reverse setting
- **WHEN** a reverse page is scanned in a double-sided workflow
- **THEN** the reverse rotation setting SHALL be applied to it regardless of its
  final page number parity

#### Scenario: Facing pages rotate by the facing setting
- **WHEN** a facing page is scanned in a double-sided workflow
- **THEN** the facing rotation setting SHALL be applied to it

### Requirement: Extended mode inserts before a page
Extended page numbering SHALL insert each new scan before a chosen page,
optionally advancing the insertion position by a step for each subsequent scan.
Page numbers SHALL remain consecutive after each insertion.

#### Scenario: Insert before an existing page
- **WHEN** extended mode is set to insert before page 7 and a page is scanned
- **THEN** the new page SHALL become position 7 and former page 7 SHALL shift to
  position 8

#### Scenario: Position advances between scans
- **WHEN** extended mode is set to insert before page 7 with step 1 and multiple
  pages are scanned
- **THEN** the second page SHALL be inserted before position 8, the third before
  position 9, and so on

#### Scenario: Re-scanning a page after a jam
- **WHEN** a page that failed to scan is re-scanned with extended mode set to
  insert before its intended position
- **THEN** the re-scanned page SHALL land at the intended position and the
  numbering SHALL recompress to 1..n

### Requirement: Editing the number column moves a page
Editing the page-number column SHALL move the page to the entered position and
renumber accordingly. There SHALL be no separate renumber dialog.

#### Scenario: Typing a position moves the page
- **WHEN** the number of a page is edited to 7
- **THEN** the page SHALL be moved to position 7 and all pages SHALL be
  renumbered 1..n

### Requirement: Legacy sessions are renumbered on load
When a session saved with an older version (which may contain non-consecutive
page numbers) is opened, its pages SHALL be renumbered 1..n in their stored
order.

#### Scenario: Opening a legacy session with gaps
- **WHEN** a session whose pages have numbers with gaps (e.g. 1, 3, 5, 8) is
  opened
- **THEN** the pages SHALL be renumbered 1, 2, 3, 4 in their stored order

### Requirement: Reverse pass is bounded by facing pages
In double-sided mode the maximum number of reverse pages SHALL equal the number
of facing pages scanned in the current batch.

#### Scenario: Reverse pass limit
- **WHEN** n facing pages have been scanned and the side is switched to reverse
- **THEN** the scan dialog SHALL limit the number of scanable reverse pages to n

### Requirement: Page ranges refer to positions
Page-range selectors (print, save, process) SHALL interpret page numbers as
1-based positions in the current document order.

#### Scenario: Print range maps to positions
- **WHEN** the user prints page range 2-4 of a 10-page document
- **THEN** the 2nd, 3rd, and 4th pages in document order SHALL be printed
