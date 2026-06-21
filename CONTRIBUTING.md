# Contributing

Thanks for contributing to `ha-ynblue`.

## Scope

This repository is a Home Assistant custom integration for YNEOM YnBlue pool controllers. Contributions should prioritize:

- runtime reliability
- safe command handling
- maintainable Home Assistant patterns
- clear user-facing documentation

## Local Development

1. Create and activate a Python virtual environment.
2. Install test dependencies:

   ```bash
   pip install -r requirements_test.txt
   ```

3. Run validation before opening a pull request:

   ```bash
   ruff check .
   pytest
   ```

## Engineering Rules

- Keep all source code, identifiers, and documentation in English.
- Do not add undocumented cloud endpoints or destructive commands without strong validation.
- Prefer explicit helper methods and small units over clever abstractions.
- Add or update tests for every runtime fix or behavior change.
- Redact credentials, tokens, account identifiers, and precise location data from logs and fixtures.

## Pull Requests

Please include:

- a concise description of the change
- the user-facing impact
- the validation you ran locally
- any screenshots, logs, or diagnostics needed to explain the behavior

## Release Notes

When a change should appear in release notes, describe it in terms of:

- Added
- Changed
- Fixed
- Upgrade notes
