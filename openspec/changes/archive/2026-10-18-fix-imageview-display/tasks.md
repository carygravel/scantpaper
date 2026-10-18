## 1. Regression tests (TDD)

- [x] 1.1 Add a real-layout test in `src/scantpaper/tests/test_imageview.py`
      that presents a window containing an `ImageView` under pytest-xvfb,
      sets a pixbuf with zoom-to-fit while the widget has no usable
      allocation, pumps the main loop until the first allocation, and
      asserts the zoom and offset were fitted (currently fails)
- [x] 1.2 Add a real-layout test that the image area is non-collapsed at
      startup in every viewer mode: build the window, present it, pump
      the main loop, and assert the `ImageView` allocation height > 0
      for `tabbed`, `horizontal`, and `vertical`
- [x] 1.3 Add a unit test that `do_size_allocate` re-fits when
      `zoom_is_fit` is active and chains up before reading the
      allocation

## 2. ImageView fixes

- [x] 2.1 In `src/scantpaper/imageview.py`, replace the dead
      `notify::width`/`notify::height` connections with a
      `do_size_allocate` vfunc override that chains up first and
      re-runs `zoom_to_box()` when `zoom_is_fit` is active
- [x] 2.2 Guard `to_widget_coords` to treat a `None` offset as (0, 0)
      and `_draw_func` to skip the image paint (background only) when
      the offset is `None`

## 3. Pane initialisation

- [x] 3.1 In `src/scantpaper/app_window.py` `_pack_viewer_tools`, call
      `_init_split_pane` on the outer `_vpaned` in tabbed mode, and in
      split modes apply the default position to `_vpaned` as well as
      the existing inner-pane calls
- [x] 3.2 Guard the outer `_vpaned` default-position initialisation so
      it applies only on first packing, not on view-mode switches

## 4. Gate

- [x] 4.1 Run the full suite: `pytest` passes with coverage thresholds
      met and no worse uncovered/partially-covered line counts
- [x] 4.2 `ruff check`, `ruff format --check`, and `ty check .` are clean
- [x] 4.3 Manually verify under xvfb that a scan (mocked SANE) and a
      `--import` both display the page in the image view in tabbed and
      split modes, and that resizing the window re-fits the page
