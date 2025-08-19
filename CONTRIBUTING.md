# Contribution Guidelines for Scantpaper

This document provides guidelines for contributing to the scantpaper project. By following these guidelines, you can help ensure that your contributions are consistent with the project's standards and easily integrated into the codebase.

## Project Overview

Scantpaper is a graphical user interface (GUI) application for scanning, processing, and managing documents. It allows users to create PDF or DjVu files from scanned images, with features such as batch scanning, optical character recognition (OCR), and image editing. The project is written in Python and uses the GTK+ toolkit for its user interface.

## Getting Started

Before you begin, make sure you have a local clone of the scantpaper repository and have installed the necessary dependencies.

### Prerequisites

- Python 3
- The python dependencies listed in `requirements.txt` and system-level
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
    pip install -r requirements.txt
    ```
    You will also need to install the system-level dependencies mentioned in the `README.md` file.

## How to Contribute

When contributing to scantpaper, please follow these steps:

1.  **Discuss your changes:** Before you start working on a new feature or bug fix, it's a good idea to discuss it with the project maintainers. You can do this by creating an issue on the GitHub repository.

2.  **Create a new branch:** For each new feature or bug fix, create a new branch in your local repository:

    ```bash
    git checkout -b my-new-feature
    ```

3.  **Make your changes:** Write your code, following the project's coding style and conventions.

4.  **Write or update tests:** If you are adding a new feature, please include tests that cover the new functionality. If you are fixing a bug, consider adding a test that reproduces the bug and verifies that your fix resolves it.

5.  **Run the tests:** Before submitting your changes, make sure that all tests pass:

    ```bash
    pytest
    ```

6.  **Commit your changes:** Write a clear and concise commit message that explains the purpose of your changes.

7.  **Push your changes:** Push your changes to your forked repository.

8.  **Create a pull request:** Open a pull request on the scantpaper GitHub repository.

## Coding Style

Please run `black` over new or changed code to automatically format it.

Scantpaper follows the PEP 8 style guide for Python code. Please ensure that your code adheres to these guidelines. You can use a linter like `pylint` to check your code for compliance. The `.pylintrc` file in the root of the repository contains the project's linting configuration.

Please ensure that any changes made do not reduce the pylint score.

## Commit messages

Please ensure that all commits have meaningful messages:

1. Start with at least on [git emoji](see https//:gitmoji.dev)
2. Include at least one sentence describing the change

## Testing

Scantpaper uses `pytest` for testing. The tests are located in the `tests/` directory. To run the tests, use the following command:

```bash
pytest
```

This will run all tests and generate a coverage report. Please ensure that your changes do not decrease the test coverage.

## Documentation

If you are adding a new feature, please update the documentation to reflect the changes. The documentation is located in the `README.md` file.

## Submitting a Pull Request

When you are ready to submit your changes, please create a pull request on the scantpaper GitHub repository. In your pull request, please include the following information:

-   A clear and concise title and description of your changes.
-   A reference to the issue that your pull request addresses (if applicable).
-   A summary of the changes you have made.
-   Any additional information that may be helpful for the reviewers.

Thank you for contributing to scantpaper!
