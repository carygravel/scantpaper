## ADDED Requirements

### Requirement: Atomic undo and redo of multi-page batches
Undo and redo SHALL treat a batch of page operations (a run of page edits
made as part of one user action across several pages) as a single atomic
step. When the worker thread runs in batch mode, a batch of page
replacements SHALL be recorded under one action id so that one undo reverts
the whole batch and one redo re-applies it.

#### Scenario: Batch of page edits shares one undo step
- **WHEN** the worker thread is placed in batch mode and several page
  operations run within the batch
- **THEN** the batch SHALL produce a single snapshot / action id rather than
  one per page

#### Scenario: Undo of a batch restores every affected page
- **WHEN** a batch of page operations completes and undo is triggered once
- **THEN** every page modified within the batch SHALL be restored to its
  pre-batch state in a single undo step

#### Scenario: Redo of a batch re-applies every affected page
- **WHEN** a batch is undone and redo is triggered once
- **THEN** every page modified within the batch SHALL be re-applied in a
  single redo step

#### Scenario: Single-page operations remain one step each
- **WHEN** a page operation is applied to a single page (outside a batch)
- **THEN** it SHALL record exactly one undo step, unchanged from current
  behaviour
