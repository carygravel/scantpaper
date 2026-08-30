# Contribution Guidelines for Scantpaper

This document provides guidelines for contributing to the scantpaper project.
By following these guidelines, you can help ensure that your contributions are
consistent with the project's standards and easily integrated into the codebase.

## Project Overview

Scantpaper is a graphical user interface (GUI) application for scanning,
processing, and managing documents. It allows users to create PDF or DjVu files
from scanned images, with features such as batch scanning, optical character
recognition (OCR), and image editing. The project is written in Python and uses
the GTK+ toolkit for its user interface.

## Architecture

*   **Overall Architecture:** Monolithic Desktop Application. It is a standalone
    GUI application, not a client-server or web application.
*   **Directory Structure:**
    *   `scantpaper/`: Contains the primary Python source code for the application.
    *   `scantpaper/dialog/`: Contains UI dialog components.
    *   `dev/`: Contains development-related scripts (e.g., `generate_pot.py` for
        translations).
    *   `tests/`: Contains all unit and integration tests, managed by pytest.
*   **Main Entrypoint:** `scantpaper/app.py`. When installed, the package
    provides a `gui_scripts` entrypoint via `pyproject.toml`.
*   **Key Dependencies:** `ocrmypdf`, `img2pdf`, `pikepdf`, `python-sane`,
    `PyGObject`, `pycairo`, `tesserocr`, `python-iso639`. All listed in
    `pyproject.toml`.

## Getting Started

Before you begin, make sure you have a local clone of the scantpaper repository
and have installed the necessary dependencies.

### Prerequisites

- Python 3
- The python dependencies listed in `pyproject.toml` and system-level
  dependencies given in the `README.md` file.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/carygravel/scantpaper.git
    cd scantpaper
    ```

2.  **Install dependencies:**

    It is recommended to use a virtual environment to manage dependencies:

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    ```
    You will also need to install the system-level dependencies mentioned in
    the `README.md` file.

## How to Contribute

When contributing to scantpaper, please follow these steps:

1.  **Discuss your changes:** Before you start working on a new feature or bug
fix, it's a good idea to discuss it with the project maintainers. You can do
this by creating an issue on the GitHub repository.

2.  **Create a new branch:** For each new feature or bug fix, create a new
branch in your local repository:

    ```bash
    git checkout -b my-new-feature
    ```

3.  **Make your changes:** Write your code, following the project's coding
style and conventions.

4.  **Write or update tests:** If you are adding a new feature, please include
tests that cover the new functionality. If you are fixing a bug, consider
adding a test that reproduces the bug and verifies that your fix resolves it.

5.  **Run the tests:** Before submitting your changes, make sure that all tests pass:

    ```bash
    pytest
    ```

6.  **Commit your changes:** Write a clear and concise commit message that
explains the purpose of your changes.

7.  **Push your changes:** Push your changes to your forked repository.

8.  **Create a pull request:** Open a pull request on the scantpaper GitHub
repository.

## Coding Style

Please run `black` over new or changed code to automatically format it.

This is best run as pre-commit hook:

    ```bash
    sudo apt install pre-commit
    pre-commit install
    ```

This will install the hook for black, configured in `.pre-commit-config.yaml`.

Scantpaper follows the PEP 8 style guide for Python code. Please ensure that
your code adheres to these guidelines. Please use `pylint` to check your code.
The `.pylintrc` file in the root of the repository contains the project's
linting configuration.

Please ensure that any changes made do not increase the number of pylint warnings.

### Lint Suppression

**Ask before adding any suppression.** Do not add `pylint: disable` or `noqa`
comments on your own initiative. If a linter warning cannot be resolved by
correcting the code, stop and discuss the case with a maintainer first, and only
add the suppression after it has been explicitly approved. Approvals may be
given per-case or once for a clearly-scoped class of cases (e.g. "BL001 on
thread dispatch boundaries").

Whenever a suppression is approved and added, it must carry an explanation that
states why the warning is being suppressed. Either:
- put the explanation inline after an em dash (`# noqa: RULE — reason`), or
- put a comment line immediately above the offending code explaining the reason.

Keep suppressions intentional, documented, and limited to cases where they are
truly necessary.

Do not add rules to the `ignore` list in `pyproject.toml` without prior
agreement from a maintainer. Each suppression should be discussed and justified
in the pull request that introduces it.

### Line Length

Wrap markdown documentation at 80 characters per line.

### Docstrings

For single-line docstrings, use straight double quotes (`"..."`). For
multiline docstrings, use triple double quotes (`"""..."""`). Keep the
convention consistent within a file; prefer single-line docstrings when the
full text fits on one line.

### Type Annotations

Do not use `typing.Any` (or bare `Any`) as a type annotation. `Any` disables
type checking entirely and hides real bugs, so prefer the most specific type
that is accurate. Where a value genuinely has several possible types, use a
`Union` (e.g. `int | None`, `list | tuple | None`) of the concrete types; for
a truly polymorphic payload use `object` rather than `Any`, so consumers are
forced to narrow it explicitly.

## Commit messages

Please ensure that all commits have meaningful messages:

1. Start with at least one [git emoji](see https://gitmoji.dev)
2. Include at least one sentence describing the change

## Testing

Scantpaper uses `pytest` for testing. The tests are located in the `tests/`
directory. To run the tests, use the following command:

```bash
pytest
```

This will run all tests and generate a coverage report. Please ensure that your
changes do not increase the number of uncovered or partially-covered lines.

## Documentation

If you are adding a new feature, please update the documentation to reflect the
changes. The documentation is located in the `README.md` file.

## Submitting a Pull Request

When you are ready to submit your changes, please create a pull request on the
scantpaper GitHub repository. In your pull request, please include the
following information:

-   A clear and concise title and description of your changes.
-   A reference to the issue that your pull request addresses (if applicable).
-   A summary of the changes you have made.
-   Any additional information that may be helpful for the reviewers.

Thank you for contributing to scantpaper!
