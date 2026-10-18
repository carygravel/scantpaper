# Tasks: disable-gl-renderer-in-tests

## 1. Pin the renderer environment

- [x] 1.1 In `src/scantpaper/conftest.py`, add
      `os.environ.setdefault("GDK_DISABLE", "gl")` and
      `os.environ.setdefault("GSK_RENDERER", "cairo")` at the top of the
      module, before the `gi` import, with a comment explaining that GTK4's
      auto-selected GL renderer segfaults on pytest-xvfb's software EGL stack.

## 2. Colour depth

- [x] 2.1 In `pyproject.toml` `[tool.pytest.ini_options]`, add
      `xvfb_colordepth = "24"` with a brief comment.

## 3. Verification

- [x] 3.1 Run `pytest -q` (full suite) three consecutive times on the
      affected machine; all must pass with no `libEGL` warnings in the
      output.
- [x] 3.2 Confirm `ruff check .`, `ruff format --check .` and `ty check .`
      stay clean.
