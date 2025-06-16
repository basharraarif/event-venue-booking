# Linting and Formatting Guide

This document provides instructions for installing and running linters and formatters for both the backend and frontend of the Event Booking Platform.

## Backend (Python/Django)

The backend uses `flake8` for linting and `black` for formatting.

### Installation

1.  Navigate to the backend directory:
    ```bash
    cd event_booking_platform_backend
    ```
2.  Ensure you have Poetry installed.
3.  Install development dependencies (including `flake8` and `black`):
    ```bash
    poetry install --only dev
    ```

### Running Checks

From within the `event_booking_platform_backend` directory:

1.  **Flake8 (Linter)**:
    To check for PEP 8 style violations, programming errors, and code complexity:
    ```bash
    poetry run flake8 .
    ```
2.  **Black (Formatter - Check Mode)**:
    To check which files would be reformatted by Black without actually changing them:
    ```bash
    poetry run black . --check --diff
    ```

### Auto-formatting

From within the `event_booking_platform_backend` directory:

1.  **Black (Formatter - Apply Changes)**:
    To automatically reformat files according to Black's style:
    ```bash
    poetry run black .
    ```

## Frontend (Next.js/TypeScript)

The frontend uses `ESLint` for linting and `Prettier` for formatting.

### Installation

1.  Navigate to the frontend directory:
    ```bash
    cd event_booking_platform_frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
    (or `yarn install` if you are using Yarn)

### Running Checks

From within the `event_booking_platform_frontend` directory:

1.  **ESLint (Linter)**:
    To check for JavaScript/TypeScript code quality and style issues:
    ```bash
    npm run lint
    ```
    For a quieter output, often used in CI:
    ```bash
    npm run lint:ci
    ```
    (The `lint:ci` script is configured as `eslint . --ext .ts,.tsx --quiet`)

2.  **Prettier (Formatter - Check Mode)**:
    To check which files would be reformatted by Prettier without actually changing them:
    ```bash
    npm run format:check
    ```
    (This script is configured as `prettier --check .`)

### Auto-formatting

From within the `event_booking_platform_frontend` directory:

1.  **Prettier (Formatter - Apply Changes)**:
    To automatically reformat files according to Prettier's style:
    ```bash
    npm run format
    ```
    (This script is configured as `prettier --write .`)

## Important Notes

*   **Persistent Syntax Error**:
    There is a known persistent syntax error in the frontend file `event_booking_platform_frontend/src/app/payment-status/page.tsx`. This file is currently being ignored by ESLint (via `.eslintignore`) and Prettier (via `.prettierignore`) to allow linting and formatting checks to proceed for the rest of the project. This error needs to be investigated and fixed separately.
*   It's recommended to run these checks and formatters before committing code to maintain consistency across the codebase.
*   Consider integrating these checks into pre-commit hooks for automation.
