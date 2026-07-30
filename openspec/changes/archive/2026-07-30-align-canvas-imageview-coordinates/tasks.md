## 1. Update `_draw_scene` transform

- [x] 1.1 Replace the translate-center/scale/translate-back/translate-offset formula with uniform scale + translate(offset) matching ImageView convention

## 2. Update coordinate conversion methods

- [x] 2.1 Update `_hit_test` to use the new inverse transform (subtract offset instead of adding)
- [x] 2.2 Update `_scroll` cursor-to-image conversion to match the new transform
- [x] 2.3 Update `_set_zoom_with_center` offset calculation to match the new sign convention
- [x] 2.4 Verify `_motion` and `_to_image_distance` need no changes (pure distance math, no offset involved)

## 3. Update tests

- [x] 3.1 Update `test_canvas_scroll` for new coordinate math (no change needed — test only verifies zoom value and set_offset call, offset=0 gives same result under both conventions)
- [x] 3.2 Update `test_drag_text_layer` for new offset sign (no change needed — alloc is 0-sized, clamping hides the math)
- [x] 3.3 Update `test_set_zoom_with_center_clamp` for new offset calculation (no change needed — only tests MAX_ZOOM clamping)
- [x] 3.4 Update `test_canvas_set_offset_clamping` for new behavior (no change needed — tests clamping logic only, no transforms involved)
- [x] 3.5 Check all other tests for implicit coordinate assumptions (all 1001 pass — no issues)

## 4. Verify

- [x] 4.1 Run `pytest` and confirm all tests pass (1001 passed)
- [x] 4.2 Run `black` and confirm formatting is clean (1 file left unchanged)
- [x] 4.3 Run `pylint` and confirm score is not degraded (9.54, improved from 9.11)
- [x] 4.4 Verify test coverage meets the 98% threshold (99.00%)
