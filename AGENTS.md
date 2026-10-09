# Collaboration Guide

This document provides essential context for anyone working on this project. Adhering to these guidelines will ensure consistency and maintain code quality.

## 1. Project Overview & Purpose

-   **Primary Goal:** To provide a graphical user interface (GUI) for producing PDFs or DjVus from scanned documents. The application allows for scanning, editing (cropping, rotating), and saving documents with OCR and metadata support.
-   **Business Domain:** Document Management and Scanning. This is a utility application for end-users.

## 2. Core Technologies & Stack

-   **Languages:** Python 3.
-   **Frameworks & Runtimes:**
    -   GUI: PyGObject with GTK3.
    -   Runtime: Python 3.
-   **Databases:** SQLite is used to store all session data, which was a major architectural change in the rewrite from Perl to Python.
-   **Key Libraries/Dependencies:**
    -   `ocrmypdf`: Core dependency for creating OCR'd PDFs.
    -   `img2pdf`: Used for PDF conversion.
    -   `python-sane`: For interfacing with SANE-compatible scanners.
    -   `PyGObject`: Python bindings for GTK3.
    -   `pycairo`: For 2D graphics.
    -   `tesserocr`: OCR.
-   **Package Manager(s):** `pip` is used for Python dependencies, managed via `pyproject.toml`. System-level dependencies are managed by the OS package manager (e.g., `apt`).

## 3. Architectural Patterns

-   **Overall Architecture:** Monolithic Desktop Application. It is a standalone GUI application, not a client-server or web application.
-   **Directory Structure Philosophy:**
    -   `/src/scantpaper`: Contains the primary Python source code for the
        application.
    -   `/src/scantpaper/dialog`: Contains UI dialog components.
    -   `/dev`: Contains development-related scripts (e.g., `generate_pot.py`
        for translations). This folder is not a Python package.
    -   `/src/scantpaper/tests`: Contains all unit and integration tests,
        managed by pytest.

## 4. Coding Conventions & Style Guide
@MEMORY.md
-   **Markdown line length:** Wrap long lines in Markdown files (`.md`, including
    README.md and the OpenSpec artifacts) at 80 characters. There must be a very
    good reason for having any line longer than 512 characters.

-   **Formatting:** The project uses `ruff` for automated code formatting and linting.
-   **Type checking:** The project uses `ty` (the type checker Zed uses for
    Python) for static type checking. Its rule blacklist lives in
    `[tool.ty.rules]` in `pyproject.toml`; keep `ty check .` clean in the same
    manner as `ruff`.
-   **Naming Conventions:**
    -   `classes`: `PascalCase` (e.g., `Application`, `ApplicationWindow`).
    -   `variables`, `functions`: `snake_case` (e.g., `register_icon`, `parse_arguments`).
    -   This follows standard PEP 8 conventions.
-   **Constants:** Define any constant that is used in more than one place
    (across modules, or across code and tests) in `src/scantpaper/const.py` and
    import it from there, rather than duplicating the literal. This keeps a
    single source of truth for shared values (e.g. `MM_PER_INCH`,
    `POINTS_PER_INCH`, `A4_WIDTH_MM`). File-local values that are used in only
    one place may stay as a local module constant.
-   **API Design:** Not applicable, as this is a desktop GUI application, not a web service.
-   **Error Handling:** Standard `try...except` blocks are used for error handling. The application also features a robust logging system configured via command-line arguments, which is crucial for diagnostics.

## 5. Key Files & Entrypoints

-   **Main Entrypoint(s):** `src/scantpaper/app.py` is the main entrypoint for
    the application. From a source checkout it is run as
    `PYTHONPATH=src python3 -m scantpaper.app`.
-   **Configuration:**
    -   User configuration is stored in `~/.config/scantpaperrc`.
    -   Project configuration for development tools includes: `pyproject.toml`.
-   **CI/CD Pipeline:** A `.github/workflows` directory exists for GitHub Actions.

## 6. Development & Testing Workflow

-   **Local Development Environment:** Set up a Python virtual environment and
    install dependencies using `pip install .`. From a source checkout the
    application is run with `PYTHONPATH=src python3 -m scantpaper.app`.
-   **Testing:** Tests are written using the `pytest` framework. They can be
    executed by running the `pytest` command in the root directory; tests run
    directly against the source tree via `pythonpath = ["src"]`. The
    `pyproject.toml` file configures test runs to include coverage reports and
    to fail if coverage drops below a certain threshold.
-   **Translations:** Translation strings are marked with `_()` in the source.
    The workflow for handling translations is:
    1. Regenerate the translation template with
       `PYTHONPATH=src python3 dev/generate_pot.py`, which creates the `.pot`
       file.
    2. Missing strings in `po/scantpaper/*.po` may be translated locally, but
       every such
       addition MUST be marked `#, fuzzy` (needs review). Never add a
       translation that is not marked fuzzy. The point of the marker is to
       hold every new translation behind review until a translator confirms
       it, not to block a release: a fuzzy translation is never shown to the
       user, because it falls back to the English msgid (see the release
       gate below), so an unreviewed translation cannot reach users by
       accident.
    3. A `#, fuzzy` flag that another author or tool added MAY be cleared
       (removed) as part of a translation review, but only when the
       maintainer explicitly directs it. Do not clear a fuzzy flag on your
       own initiative, and do not alter the translated text as part of
       clearing unless specifically asked. This is the only sanctioned way
       to ship a previously-fuzzy string without a Rosetta pass; it stays
       gated on human review rather than an agent's judgement.
    4. Upload the seeded `.po` files (not just the `.pot`) to Rosetta
       (Launchpad) so translators can confirm and clear the fuzzy entries.
    5. Download the translated `.po` files from Rosetta before a release.
    6. Ensure every `po/scantpaper/*.po` passes the deterministic catalog
       checks: run
       `PYTHONPATH=src python3 dev/check_po.py` (CI enforces the same via
       `test_po_files.py`), which runs `msgfmt --check` (format-specifier
       drift, escaping, plural-entry counts) and validates each catalog's
       `Plural-Forms` header against CLDR. Never disable a check to make a
       catalog pass.
    Source conventions: counted strings must use `ngettext`, never `_()`;
    new-language catalogs must declare a CLDR-correct `Plural-Forms`
    header.
    `dev/check_po.py` also reports source-side *advisories* for strings that
    are hard to translate, which is where translation-authoring guidance
    comes from. The conventions to follow so the warnings stay at zero:
    - Never build a translatable sentence out of parts. A string ending in a
      colon or an ellipsis with no value of its own is a concatenation
      fragment: it fixes English word order into the translation. Pass the
      value in the same string with a named field, e.g.
      `_("Error opening device: %(status)s") % {"status": status}`. The same
      applies to a translated sentence joined to a non-translated list.
    - Never hand-write a plural as `file(s)` or `file(es)`. Use `ngettext`;
      a parenthesised unit or abbreviation such as `(Mb)` is fine.
    - Do not let two msgids differ only by case, such as `_Ok` and `_OK`.
      Use `_OK` for a mnemonic on a button, matching the label's own
      capitalisation.
    - Match the case of the surrounding text for unit labels: a `ppi` next to
      a spin button is lower case, an `OK` in a dialog is upper.
    - Keep msgids short; over 200 characters is flagged as a translation
      effort risk.
    Release gate: only non-fuzzy translations ship. Release builds never pass
    `--use-fuzzy` to `msgfmt`, so a fuzzy translation is excluded from the
    release and the English msgid is shown instead; a fuzzy string is
    therefore never visible to the user. A release is not blocked by the
    presence of fuzzy entries.
-   **CI/CD Process:** The `.github/workflows/test.yml` file runs the test suite.

## 7. Contribution Guidelines
  - Follow TDD, DRY & YAGNI
  - Before finishing a task ensure:
    - Any changes visible to the user are documented in README.md 
    - *all* tests pass (`pytest`)
    - the code is formatted with `ruff`.
    - the numbers of uncovered and partially covered lines are the same or
      better. The only acceptable newly-uncovered lines are the type-only
      imports inside `if TYPE_CHECKING:` blocks, which by design never execute;
    - no ruff linting errors. Do not disable checks with
      `noqa=` or `per-file-ignores` without first obtaining explicit
      agreement from the maintainer. The only standing exceptions are
      `gi.repository` imports following `gi.require_version()` and the
      pre-existing test-suite suppressions listed in `pyproject.toml`.
    - no `ty` type-check diagnostics (`ty check .` reports none). As with
      ruff, do not add rules to the `[tool.ty.rules]` blacklist without
      explicit agreement from the maintainer.
      On this development machine `ty` is not on `PATH`; it is installed by
      Zed and can be run directly at
      `/home/jeff/.local/share/zed/languages/ty/ty-0.0.84/ty-x86_64-unknown-linux-gnu/ty`.
-   **Security:** Be mindful of security. Do not hardcode secrets or keys.
-   **Dependencies:** To add a new Python dependency, add it to `pyproject.toml`. Ensure it is available on common distributions or via `pip`.
-   **OpenSpec:** The `openspec` CLI manages change workflows. It is installed globally via npm: `npm install -g @fission-ai/openspec@latest`.
-   **imports:** The project uses package-absolute imports for first-party
    modules: import statements always carry a leading `scantpaper` prefix,
    e.g. `from scantpaper.const import VERSION`.

## 8. Spec-Driven Development (SDD)

Non-trivial changes **must** follow a spec-first workflow via OpenSpec before any
implementation begins.

-   **What counts as non-trivial** (any one of these qualifies):
    -   Adds or changes user-visible behaviour (UI, CLI options, output files).
    -   Changes architecture, data model, or inter-module contracts.
    -   Touches more than one module, or more than ~50 lines.
    -   Adds/removes a dependency.
    -   Fixes a bug whose root cause is not immediately obvious from the report.
-   **What is trivial** (may proceed directly): typo fixes, comment/log message
    updates, formatting, and small self-contained fixes with an obvious cause
    and a test.
-   **Workflow:** create a change proposal first (`openspec new change`, or the
    `/opsx-propose` skill), get it approved, then implement against its tasks
    (`/opsx-apply-change`). Do not start coding with only a verbal description.
-   Exploration and thinking are encouraged at any time (e.g. `/opsx-explore`),
    but insights must be captured into proposal/spec/design artifacts before
    they turn into code.
