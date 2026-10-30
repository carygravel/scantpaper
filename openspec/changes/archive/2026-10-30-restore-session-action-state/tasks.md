# Tasks

## 1. Restore the action state from the session history

- [x] 1.1 Add a helper that returns the latest recorded action from both the
  page-order and selection history, defaulting to 0 when no action is
  recorded. Verify with focused tests for an empty history, a page-only
  history, and a history whose newest action has no page-order rows.
- [x] 1.2 Use the helper in `can_redo()` so open and redo share one definition
  of the latest action. Verify the existing undo/redo tests pass with
  `pytest src/scantpaper/tests/test_docthread.py -k "undo or redo"`.
- [x] 1.3 In `DocThread.open()`, assign `_action_id` from the helper
  unconditionally, with 0 for an empty history, and make the no-history value
  explicit instead of relying on an unchecked `cast("int", ...)`. Verify the
  updated open-session unit tests and `ty check .` pass.

## 2. Cover reopening at the document level

- [x] 2.1 Add a regression test that creates an empty session, reopens it,
  adds a page, and asserts the page is added as exactly the first undo step
  and that undo returns the document to empty. Verify it fails before the
  open-path change and passes after it.
- [x] 2.2 Add a regression test that adds a page, deletes every page, saves
  with `save_as()`, reopens, and asserts the document is empty and undo
  restores the removed page. Verify it fails before the fix, when the page
  reappears on reopen.
- [x] 2.3 Add a regression test that opens a populated session and then a
  second empty session, adds a page there, and asserts the first session's
  history is not inherited and the new page is action 1.
- [x] 2.4 Add a regression test that reopening an empty session offers
  neither undo nor redo.
- [x] 2.5 Document the reopened-session behaviour in the README Sessions
  section and add a 4.0.2 changelog entry. Verify the text names both the
  empty-session scan fix and the cleared-session reopen.

## 3. Verification

- [x] 3.1 Run the full quality gates - `pytest`, `ruff format --check .`,
  `ruff check .`, `ty check .`, and `openspec validate
  restore-session-action-state --strict` - and verify they all pass with
  coverage unchanged or improved.

## Workflow follow-up

- Archive the change after the implementation is merged and the project's
  review requirements are satisfied.
- Verify the archived `session-persistence` spec contains the two added
  requirements.
