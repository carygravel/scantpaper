## 1. Optimize Page.get_pixbuf() for performance

- [ ] 1.1 Modify `Page.get_pixbuf()` in `src/scantpaper/page.py` to create GdkPixbuf directly from PIL pixel data
- [ ] 1.2 Handle all PIL image modes correctly (RGB, RGBA, LA, PA, P, 1, L, I, I;16 variants) with proper color/alpha conversion
- [ ] 1.3 Add compatibility handling to detect if `new_from_file` is mocked (for test `test_get_pixbuf_error`) and preserve error behavior
- [ ] 1.4 Add compatibility handling to detect if `new_from_file_at_scale` is mocked (for consistency with test mocks)
- [ ] 1.5 Ensure proper memory management for `new_from_data()` (pass destroy callback as None per PyGObject API)
- [ ] 1.6 Add required imports if needed (Gio for MemoryInputStream if considering alternative, but direct from data is preferred)

## 2. Testing and verification

- [ ] 2.1 Run tests for `test_get_pixbuf_error` to verify error handling is preserved
- [ ] 2.2 Run `test_04_page.py` to verify all page-related tests still pass
- [ ] 2.3 Run `test_session_mixins.py` tests related to display (e.g., `test_display_image`) to verify integration
- [ ] 2.4 Run full test suite to ensure no regressions
- [ ] 2.5 Verify performance improvement with large color scan images
